# This file is part of Superdesk.
#
# Copyright 2013, 2021 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

"""Commands to save, restore, list and upgrade full dumps or partial records"""


import sys
import os
import signal
import time
import logging
import platform
import shutil
from multiprocessing import Process, Lock
import multiprocessing.synchronize
from datetime import datetime
from enum import IntEnum
from pathlib import Path
from typing import Optional, Union, List

from bson.json_util import dumps, loads
from pymongo.errors import OperationFailure
import superdesk
from . import data_updates, flush_elastic_index


logger = logging.getLogger(__name__)

BUF_LEN = 2048

State = IntEnum(
    "State",
    "INIT METADATA_KEY METADATA_OBJECT_EXPECTED METADATA_OBJECT COLLECTION COLLECTION_NAME COLLECTION_COLON "
    "COLLECTION_SQ_BRACKET COLLECTION_OBJECT_EXPECTED COLLECTION_OBJECT COLLECTION_OBJECT_END COLLECTION_END",
)

DUMP_NAME = "superdesk-dump"
DUMP_DIR = "dump/full"
RECORD_NAME = "superdesk-record"
RECORD_DIR = "dump/records"
BASE_DUMP_CONFIRM_MSG = "{base_dump_p} will be restored, all your data will be erased, do you confirm? (y/N)"
METADATA_KEY = "_sd_dump_metadata"

if platform.system() in ("Linux", "Darwin") and sys.stdout.isatty():
    STYLE_RESET = "\033[0m"
    STYLE_TITLE = "\033[4m"
    STYLE_NAME = "\033[1m"
    STYLE_DESC = "\033[36m"
    STYLE_ERR = ""
    INFO = f"\033[1;37m\033[44m ℹ️ {STYLE_RESET}"
else:
    STYLE_RESET = ""
    STYLE_TITLE = ""
    STYLE_NAME = ""
    STYLE_DESC = ""
    STYLE_ERR = ""
    INFO = "[i] "


def get_dest_path(dest: Union[Path, str], dump: bool = True) -> Path:
    """Find directory or file from given dest

    :parap dest: either full path to the destination or its name
    :param dump: True if we're looking for a full dump, False if we're looking for a record
    :return: found path
    :raises ValueError: No dump or record found at this path
    """
    dest = Path(dest)
    base = Path(DUMP_DIR if dump else RECORD_DIR)
    for test_path in (dest, base / dest, dest.with_suffix(".json"), base / dest.with_suffix(".json")):
        if test_path.exists():
            return test_path.resolve()
    raise ValueError(f"There is no {'dump' if dump else 'record'} at {dest}.")


def draw_box_title(title: str) -> None:
    """Print a title with a box around"""
    print()
    print(f"┏{'━' * len(title)}┓")
    print(f"┃{title}┃")
    print(f"┗{'━' * len(title)}┛")
    print()


def parse_dump_file(
    dump_file: Path,
    single_file=True,
    metadata_only: bool = False,
    keep_existing: bool = False,
) -> dict:
    """Restore database from a single file

    :param dump_file: path to the dump file
    :param single_file: True if the dump is in a single file, otherwise it's a collection file from a dump directory
    :param metadata_only: if True only return metadata and don't restore anything from rest of dump
    :param keep_existing: if True collections won't be erased before dumped data will be restored

    :return: metadata
    """
    db = superdesk.app.data.pymongo().db
    # we use a state machine to parse JSON progressively, and avoid memory issue for huge databases
    if single_file:
        collection_name = None
        collection = None
        state = State.INIT
    else:
        collection_name = dump_file.stem
        collection = db.get_collection(collection_name)
        if collection_name == METADATA_KEY:
            state = State.METADATA_OBJECT_EXPECTED
        else:
            state = State.COLLECTION_SQ_BRACKET
            if not keep_existing:
                collection.delete_many({})
    metadata = {}
    obj_buf = []
    escaping = False
    par_count = 0
    inserted = 0
    with dump_file.open() as f:
        buf = f.read(BUF_LEN)
        while buf:
            for idx in range(len(buf)):
                c = buf[idx]
                if state == State.INIT:
                    if c in (" ", "\n"):
                        pass
                    elif c == "{":
                        state = State.METADATA_KEY
                    else:
                        raise ValueError("Invalid dump file")
                elif state == State.METADATA_KEY:
                    if c in (" ", "\n"):
                        pass
                    else:
                        obj_buf.append(c)
                        if len(obj_buf) == len(METADATA_KEY) + 3:
                            if "".join(obj_buf) == f'"{METADATA_KEY}":':
                                state = State.METADATA_OBJECT_EXPECTED
                            else:
                                raise ValueError(f"Invalid dump file (state: {state})")
                elif state == State.METADATA_OBJECT_EXPECTED:
                    if c in (" ", "\n"):
                        pass
                    elif c == "{":
                        obj_buf = ["{"]
                        state = State.METADATA_OBJECT
                    else:
                        raise ValueError(f"Invalid dump file (state: {state})")
                elif state == State.METADATA_OBJECT:
                    obj_buf.append(c)
                    if c == "\\":
                        escaping = True
                    elif escaping:
                        escaping = False
                    elif c == "{":
                        par_count += 1
                    elif c == "}":
                        if par_count:
                            par_count -= 1
                        else:
                            metadata = loads("".join(obj_buf))
                            if not single_file or metadata_only:
                                return metadata
                            obj_buf.clear()
                            state = State.COLLECTION_END
                elif state == State.COLLECTION:
                    if c in (" ", "\n"):
                        pass
                    elif c == '"':
                        state = State.COLLECTION_NAME
                    else:
                        raise ValueError(f"Invalid dump file (state: {state})")
                elif state == State.COLLECTION_NAME:
                    if c == '"' and not escaping:
                        collection_name = "".join(obj_buf)
                        obj_buf.clear()
                        if not collection_name:
                            raise ValueError("Invalid dump file")
                        state = State.COLLECTION_COLON
                        collection = db.get_collection(collection_name)
                        inserted = 0
                        print(f"parsing collection {collection_name!r}")
                        if not keep_existing:
                            collection.delete_many({})
                    elif c == "\\":
                        escaping = True
                    else:
                        obj_buf.append(c)
                        escaping = False
                elif state == State.COLLECTION_COLON:
                    if c in (" ", "\n"):
                        pass
                    elif c == ":":
                        state = State.COLLECTION_SQ_BRACKET
                    else:
                        raise ValueError(f"Invalid dump file (state: {state})")
                elif state == State.COLLECTION_SQ_BRACKET:
                    if c in (" ", "\n"):
                        pass
                    elif c == "[":
                        state = State.COLLECTION_OBJECT_EXPECTED
                    else:
                        raise ValueError(f"Invalid dump file (state: {state})")
                elif state == State.COLLECTION_OBJECT_EXPECTED:
                    if c in (" ", "\n"):
                        pass
                    elif c == "]":
                        state = State.COLLECTION_END
                    elif c == "{":
                        state = State.COLLECTION_OBJECT
                        par_count = 0
                        obj_buf[:] = ["{"]
                    else:
                        raise ValueError(f"Invalid dump file (state: {state})")
                elif state == State.COLLECTION_OBJECT:
                    obj_buf.append(c)
                    if c == "\\":
                        escaping = True
                    elif escaping:
                        escaping = False
                    elif c == "{":
                        par_count += 1
                    elif c == "}":
                        if par_count:
                            par_count -= 1
                        else:
                            obj = loads("".join(obj_buf))
                            collection.insert(obj)  # type: ignore
                            inserted += 1
                            obj_buf.clear()
                            state = State.COLLECTION_OBJECT_END
                elif state == State.COLLECTION_OBJECT_END:
                    if c in (" ", "\n"):
                        pass
                    elif c == ",":
                        state = State.COLLECTION_OBJECT_EXPECTED
                    elif c == "]":
                        state = State.COLLECTION_END
                        print(f"inserted {inserted} objects")
                    else:
                        raise ValueError(f"Invalid dump file (state: {state})")
                elif state == State.COLLECTION_END:
                    if c in (" ", "\n"):
                        pass
                    elif c == ",":
                        state = State.COLLECTION
                    elif c == "}":
                        print("🏁 restore finished")
                    else:
                        raise ValueError(f"Invalid dump file (state: {state})")

            if not single_file and state == State.COLLECTION_END:
                return metadata

            buf = f.read(BUF_LEN)

    if state != State.COLLECTION_END:
        raise ValueError(f"Invalid dump file (state: {state})")
    return metadata


def get_dump_metadata(dump: Path) -> dict:
    """Helper method to get metadata from a dump file or dir"""
    if dump.is_dir():
        metadata_p = dump / f"{METADATA_KEY}.json"
        return parse_dump_file(metadata_p, single_file=False)
    else:
        return parse_dump_file(dump, metadata_only=True)


class StorageDump(superdesk.Command):
    """Dump collections from MongoDB

    Note: this command should only be used for development purpose. Use MongoDB official commands to dump or restore
    databases in production.

    Dump whole collection into either separate JSON files (one per collection) or a single one (with a single root
    object).

    Single file are easier to copy, while separate JSON files are easier to check.

    A dump is full Superdesk save, as opposed to a record which only store change made in a database (more like a diff).

    Example:

    Do a full database dump with a name and description to a single file::

        $ python manage.py storage:dump -n "demo-instance" -D "this dump includes some test data (desks, users) to run a
        basic demo of Superdesk" --single
    """

    option_list = [
        superdesk.Option("-n", "--name", help=f'destination file or directory (default: "{DUMP_NAME}_<datetime>")'),
        superdesk.Option(
            "--dest-dir",
            default=DUMP_DIR,
            help='destination directory (default: "dump", will be created if necessary)',
        ),
        superdesk.Option("-D", "--description", help="description of the archive"),
        superdesk.Option("-s", "--single", action="store_true", help="dump data in a single JSON file"),
        superdesk.Option(
            "-c",
            "--collection",
            dest="collections",
            action="append",
            help="collection to dump (DEFAULT: dump all collections)",
        ),
    ]

    def run(
        self,
        name: Optional[str],
        dest_dir: Union[Path, str],
        description: Optional[str],
        single: bool,
        collections: Optional[List[str]],
    ) -> None:
        now = time.time()
        if name is None:
            name = f"{DUMP_NAME}_{datetime.fromtimestamp(now).replace(microsecond=0).isoformat()}"
        dest_dir_p = Path(dest_dir)
        dest_dir_p.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir_p / name
        db = superdesk.app.data.pymongo().db
        collections_names = [c["name"] for c in db.list_collections()]
        dump_msg = "dumping {name} ({idx}/{total})"
        metadata = {
            "started": now,
            "executable": sys.executable,
        }
        if description:
            metadata["description"] = description
        if single:
            dest_path = dest_path.with_suffix(".json")
            with dest_path.open("w") as f:
                f.write(f"{{{dumps(METADATA_KEY)}: {dumps(metadata)},")
                for idx, name in enumerate(collections_names):
                    if collections and name in collections:
                        continue
                    print(dump_msg.format(name=name, idx=idx + 1, total=len(collections_names)))
                    f.write(f"{dumps(name)}:[")
                    collection = db.get_collection(name)
                    cursor = collection.find()
                    count = cursor.count()
                    for doc_idx, doc in enumerate(cursor):
                        f.write(f"{dumps(doc)}")
                        if doc_idx < count - 1:
                            f.write(",")
                    f.write("]")
                    if idx < (len(collections_names) - 1):
                        f.write(",")
                f.write("}")
        else:
            dest_path.mkdir()
            metadata_path = dest_path / f"{METADATA_KEY}.json"
            with metadata_path.open("w") as f:
                f.write(dumps(metadata))
            for idx, name in enumerate(collections_names):
                if collections and name in collections:
                    continue
                print(dump_msg.format(name=name, idx=idx + 1, total=len(collections_names)))
                col_path = dest_path / f"{name}.json"
                collection = db.get_collection(name)
                with col_path.open("w") as f:
                    f.write("[")
                    cursor = collection.find()
                    count = cursor.count()
                    for doc_idx, doc in enumerate(cursor):
                        f.write(f"{dumps(doc)}")
                        if doc_idx < count - 1:
                            f.write(",")
                    f.write("]")
        print(f"database dumped at {dest_path}")


class StorageRestore(superdesk.Command):
    """Restore MongoDB collections dumped with ``storage:dump``

    Example::

        $ storage:restore foobar_superdesk_dump
    """

    option_list = [
        superdesk.Option("--keep-existing", action="store_true", help="don't clear collections before inserting items"),
        superdesk.Option("--no-flush", action="store_true", help="don't flush ElasticSearch indexes"),
        superdesk.Option("archive", help="file or directory containing the database dump"),
    ]

    def run(self, archive: Union[Path, str], keep_existing: bool = False, no_flush: bool = False) -> None:
        self.keep_existing = keep_existing
        archive_path = get_dest_path(archive)
        print("💾 restoring archive")
        if archive_path.is_file():
            self.restore_file(archive_path)
        elif archive_path.is_dir():
            self.restore_dir(archive_path)
        else:
            print(f"Invalid archive path: {archive_path!r}", file=sys.stderr)
            sys.exit(1)
        if not no_flush:
            print("🚽 flushing ElasticSearch index")
            try:
                flush_elastic_index.FlushElasticIndex().run(sd_index=True, capi_index=False)
            except Exception:
                logger.exception("😭 Something went wrong")
                sys.exit(1)
        print("🏁 All done")

    def restore_file(self, archive_path: Path):
        parse_dump_file(archive_path, keep_existing=self.keep_existing)

    def restore_dir(self, archive_path: Path):
        """Restore database from a dump directory"""
        for collection_path in archive_path.glob("*.json"):
            parse_dump_file(collection_path, single_file=False, keep_existing=self.keep_existing)

        print("👷 restore finished")


class StorageStartRecording(superdesk.Command):
    """Record changes made in database until the command is stopped

    This command is intended for developers to help producing specific state (e.g. for tests), or to create a specific
    Superdesk instance e.g. for a demo.

    If you specify a base dump (with ``--base-dump``), the database will be restored to this dump before starting the
    record, and it will be associated with the record.

    If no base dump is specified, the database should be in the same state as when the record has been done when you
    restore it.

    If you use the ``--full-document`` option, the whole document will be stored in the record in case of update
    (instead of just diff), this will result in a bigger dump file, but may be applied to a database even if it was not
    exactly in the same state as when the record has been done.

    You may want to use ``--collection`` to record change only on the collections you're interested in, and avoir side
    effects.

    Example:

    Record change in vocabularies only, with a name and description, and base on "base_test_e2e_dump" dump::

        $ python manage.py storage:record -b "base_test_e2e_dump" -c vocabularies -n "test_categories"-D "prepare
          instance for categories end-to-end tests"
    """

    option_list = [
        superdesk.Option("-n", "--name", help='destination file (default: "{RECORD_NAME}_<datetime>)'),
        superdesk.Option(
            "--dest-dir",
            default=RECORD_DIR,
            help='destination directory (default: "dump", will be created if necessary)',
        ),
        superdesk.Option("-D", "--description", help="description of the record"),
        superdesk.Option("-b", "--base-dump", help="base full dump from which the record must be started"),
        superdesk.Option(
            "--force-db-reset",
            action="store_true",
            help="reset database before starting record without confirmation (⚠️ you'll loose all data)",
        ),
        superdesk.Option(
            "-F",
            "--full-document",
            action="store_true",
            help="for update operation, store full document in addition to delta)",
        ),
        superdesk.Option(
            "-c",
            "--collection",
            dest="collections",
            action="append",
            help="collections to record (DEFAULT: record all collections)",
        ),
    ]

    def run(
        self,
        name: Optional[str] = None,
        dest_dir: str = RECORD_DIR,
        description: Optional[str] = None,
        base_dump: Optional[Union[Path, str]] = None,
        force_db_reset: bool = False,
        full_document: bool = False,
        collections: Optional[List[str]] = None,
        lock: Optional[multiprocessing.synchronize.Lock] = None,
    ) -> None:
        now = time.time()
        if name is None:
            name = f"{RECORD_NAME}_{datetime.fromtimestamp(now).replace(microsecond=0).isoformat()}"
        dest_dir_p = Path(dest_dir)
        dest_dir_p.mkdir(parents=True, exist_ok=True)
        dest_path = (dest_dir_p / name).with_suffix(".json")
        applied_updates = list(data_updates.get_applied_updates())
        pymongo = superdesk.app.data.pymongo()
        db = pymongo.db
        version = tuple(int(v) for v in pymongo.cx.server_info()["version"].split("."))
        if version < (4, 0):
            raise NotImplementedError("You need to use MongoDB version 4.0 or above to use the record feature")
        metadata = {"started": now, "executable": sys.executable, "applied_updates": applied_updates}
        if base_dump is not None:
            # base dump may be the direct path of the dump to load…
            base_dump_p = get_dest_path(base_dump)
            if not force_db_reset:
                confirm = input(BASE_DUMP_CONFIRM_MSG.format(base_dump_p=base_dump_p))
                if confirm.lower() != "y":
                    print("Recording cancelled")
                    sys.exit(1)
            StorageRestore().run(keep_existing=False, archive=base_dump_p)
            metadata["base_dump"] = str(base_dump_p)
        if description:
            metadata["description"] = description
        print(f"📼🔴 recording started\nRecording at {dest_path}\nPress Ctrl-C to stop it\n\n")
        if lock is not None:
            lock.release()
        try:
            options = {"full_document": "updateLookup"} if full_document else {}
            if options:
                metadata["options"] = options
            with db.watch(**options) as stream:
                with dest_path.open("w") as f:
                    metadata_dump = dumps(metadata)
                    f.write(f'{{"metadata": {metadata_dump}, "events":[')
                    try:
                        first = True
                        for change in stream:
                            collection = change["ns"]["coll"]
                            if collection == "mongolock.lock":
                                continue
                            elif collections and collection not in collections:
                                continue
                            print(f"change in {change['ns']['coll']!r} collection")
                            if first:
                                first = False
                            else:
                                f.write(",")
                            f.write(dumps(change))
                    except KeyboardInterrupt:
                        print("\n📼⬛ recording stopped")
                    finally:
                        f.write("]}")
        except OperationFailure as e:
            if e.code == 40573:
                print(
                    "To use the record feature, you must set your MongoDB instance to be a replica. Please check "
                    "the tutorial at https://docs.mongodb.com/manual/tutorial/convert-standalone-to-replica-set/ .",
                    file=sys.stderr,
                )
                sys.exit(1)
            else:
                raise e


class StorageRestoreRecord(superdesk.Command):
    """Restore Superdesk record

    This command is to be used with a record dump, not a full database archive.

    Example::

        $ storage:restore-record record-for-some-e2e-test
    """

    option_list = [
        superdesk.Option(
            "--force-db-reset",
            action="store_true",
            help="reset database before applying record without confirmation (⚠️ you'll loose all data)",
        ),
        superdesk.Option("--skip-base-dump", action="store_true", help="do not restore base dump if any is specified"),
        superdesk.Option("record_file", help="file containing the record"),
    ]

    def run(self, record_file: Union[Path, str], force_db_reset: bool = False, skip_base_dump: bool = False) -> None:
        file_path = get_dest_path(record_file, dump=False)
        db = superdesk.app.data.pymongo().db
        with file_path.open() as f:
            record_data = loads(f.read())
            metadata = record_data["metadata"]
            base_dump = metadata.get("base_dump")
            if base_dump:
                if skip_base_dump:
                    print(f"{INFO} skipping base dump restoration as requested")
                else:
                    base_dump_p = Path(base_dump)
                    if not base_dump_p.exists():
                        raise ValueError(f"There is no database dump at {base_dump_p}")
                    if not force_db_reset:
                        confirm = input(BASE_DUMP_CONFIRM_MSG.format(base_dump_p=base_dump_p))
                        if confirm.lower() != "y":
                            print("Restoration cancelled")
                            sys.exit(1)
                    StorageRestore().run(keep_existing=False, no_flush=True, archive=base_dump_p)
            print(f"{INFO} restoring record from {datetime.fromtimestamp(metadata['started']).isoformat()}")
            description = metadata.get("description")
            if description:
                print(f"{INFO} description: {description}")
            print()
            # event documentation is available at https://docs.mongodb.com/manual/reference/change-events
            print(f"📼▶ restoring record {file_path}")
            try:
                for event in record_data["events"]:
                    op_type = event["operationType"]
                    collection_name = event["ns"]["coll"]
                    collection = db.get_collection(collection_name)
                    if op_type == "insert":
                        doc = event["fullDocument"]
                        collection.insert(doc)
                        print(f"inserted one doc in {collection_name!r}")
                    elif op_type == "update":
                        doc_id = event["documentKey"]["_id"]
                        try:
                            full_doc = event["fullDocument"]
                        except KeyError:
                            update_fields = event["updateDescription"]["updatedFields"]
                            remove_fields = event["updateDescription"]["removedFields"]
                            update_data = {"$set": update_fields, "$unset": {f: 1 for f in remove_fields}}
                            collection.update({"_id": doc_id}, update_data)
                        else:
                            collection.update({"_id": doc_id}, full_doc)
                        print(f"updated doc {doc_id!r} in {collection_name!r}")
                    elif op_type == "delete":
                        doc_id = event["documentKey"]["_id"]
                        collection.remove({"_id": doc_id})
                        print(f"removed doc {doc_id!r} from {collection_name!r}")

                    else:
                        logger.warning(f"this event type is not managed: {op_type!r}")
            except Exception:
                logger.exception("🔥 Oh no, something bad happened")
                sys.exit(1)
            print("📼⏏ record restored")

        print("🚽 flushing ElasticSearch index")
        try:
            flush_elastic_index.FlushElasticIndex().run(sd_index=True, capi_index=False)
        except Exception:
            logger.exception("😭 Something went wrong")
        else:
            print("🏁 All done")


class StorageList(superdesk.Command):
    """List Superdesk Dumps and Records"""

    def run(self) -> None:
        print(f"{STYLE_TITLE}Full Dumps{STYLE_RESET}\n")
        dump_path = Path(DUMP_DIR)
        if not dump_path.is_dir():
            print("No dump found")
        else:
            for p in dump_path.iterdir():
                try:
                    metadata = get_dump_metadata(p)
                    print(f"{STYLE_NAME}{p.stem}{STYLE_RESET}")
                    desc = metadata.get("description")
                    if desc:
                        print(f"  {STYLE_DESC}{desc}{STYLE_RESET}")
                    print()
                except Exception as e:
                    print(f"{STYLE_ERR}Error while reading dump file at {p}: {e}{STYLE_RESET}", file=sys.stderr)

        print(f"⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯\n{STYLE_TITLE}Records{STYLE_RESET}\n")
        record_path = Path(RECORD_DIR)
        if not record_path.is_dir():
            print("No record found")
        else:
            for p in record_path.iterdir():
                try:
                    with p.open() as f:
                        record = loads(f.read())
                        metadata = record["metadata"]
                    print(f"{STYLE_NAME}{p.stem}{STYLE_RESET}")
                    desc = metadata.get("description")
                    if desc:
                        print(f"  {STYLE_DESC}{desc}{STYLE_RESET}")
                    print()
                except Exception as e:
                    print(f"{STYLE_ERR}Error while reading record file at {p}: {e}{STYLE_RESET}", file=sys.stderr)


class StorageMigrateDumps(superdesk.Command):
    """Apply migration scripts on all dumps and records

    Note: the backend MUST NOT be running while this command is used.

    Migration scripts are first applied on each records: changes on collections used in the record are merged to the
    record.

    Then for full dump, migration are normally applied and dumps are updated.

    The whole process may be long.

    Be sure to validate and if necessary correct results before committing anything (specially for records).

    Example::

        $ python manage.py storage:upgrade-dumps
    """

    def do_migration(self, ori_dump: str):
        """Do records and full dumps migration

        :param ori_dump: name of the dump file with original state of database
        """
        draw_box_title("Updating Records")
        records_path = Path(RECORD_DIR)
        if not records_path.is_dir():
            print("No record found")
        else:
            records = list(records_path.iterdir())
            for idx, p in enumerate(records):
                print(f"{INFO}Restoring record {p.stem!r} [{idx+1}/{len(records)}]")
                try:
                    with p.open() as f:
                        record_data = loads(f.read())
                        metadata = record_data["metadata"]
                    # we are interested only in collections used in the record
                    collections = [e["ns"]["coll"] for e in record_data["events"]]
                    if not metadata.get("base_dump"):
                        # there is no base_dump, we restore original state of DB as base
                        # this is to avoid the "data_updates" collection to be updated on first unbased record
                        print(f"{INFO}there is no base dump in this record, we use original state")
                        StorageRestore().run(
                            archive=ori_dump,
                            keep_existing=False,
                            no_flush=True,
                        )
                    # now we restore the record
                    StorageRestoreRecord().run(record_file=p, force_db_reset=True)
                    # and start a new record to get changes made for migration
                    migration_record_name = f"migration_record_{time.time()}.json"
                    m_record_p = Path(migration_record_name)
                    lock = Lock()
                    lock.acquire()
                    record_process = Process(
                        target=StorageStartRecording().run,
                        kwargs={
                            "name": migration_record_name,
                            "dest_dir": ".",
                            "collections": collections,
                            "lock": lock,
                        },
                    )
                    print(f"{INFO}Starting migration recording process")
                    record_process.start()
                    # we have to wait for the recording to be actually started
                    lock.acquire()
                    # recording is started, we can launch the migration scripts
                    data_updates.Upgrade().run()
                    # migration is done, we stop the recording
                    if record_process.pid is None:
                        logger.error("Process ID should available!")
                    else:
                        os.kill(record_process.pid, signal.SIGINT)
                    record_process.join(5)
                    if record_process.exitcode != 0:
                        logger.error(
                            f"🔥 oh no, {p} migration recording didn't stopped successfully! Cancelling migration 🚒"
                        )
                        try:
                            m_record_p.unlink()
                        except FileNotFoundError:
                            pass
                        continue
                    # changes made during migration are now recorded in m_record_p, we have to merge them if any
                    with m_record_p.open() as f:
                        changes = loads(f.read())

                    new_events = changes["events"]
                    if not new_events:
                        print(f"{INFO}{p} doesn't seem to be modified by migration scripts, nothing to do.")
                    else:
                        # we have changes
                        # we update metadata to show the update
                        metadata.setdefault("updated", []).append({"desc": "data migration", "timestamp": time.time()})
                        # and we merge the changes
                        record_data["events"].extend(new_events)
                        with p.open("w") as f:
                            f.write(dumps(record_data))
                        print(f"{INFO}{p} has been udpated")
                except Exception:
                    logger.exception(f"😭 Error while migrating record file at {p}")

        # full dumps must be updated after records, because records may be based on them thus they must not be already
        # updated.
        draw_box_title("Updating Full Dumps")
        dump_path = Path(DUMP_DIR)
        if not dump_path.is_dir():
            print("No dump found")
        else:
            dump_files_paths = list(dump_path.iterdir())
            for idx, p in enumerate(dump_files_paths):
                print(f"{INFO}Restoring dump {p.stem!r} [{idx+1}/{len(dump_files_paths)}]")
                metadata = get_dump_metadata(p)
                StorageRestore().run(keep_existing=False, archive=p)
                print(f"{INFO}Applying data migration scripts")
                data_updates.Upgrade().run()
                print(f"{INFO}Updating dump")
                if p.is_dir():
                    shutil.rmtree(p)
                else:
                    p.unlink()
                StorageDump().run(
                    name=p.name,
                    dest_dir=p.parent,
                    description=metadata.get("description"),
                    single=p.is_file(),
                    collections=None,
                )
                print(f"{INFO}Done for {p}\n")

    def run(self) -> None:
        confirm = input(
            "You're about to apply data migration scripts to all dumps and record, this may take some time and may "
            "result in data issues, be sure to have a copy of all important dumps and records first, and do not let "
            "the backend running while the migration is in progress. Do you want to continue? (y/N) "
        )
        if confirm.lower() != "y":
            print("Dumps migration cancelled")
            sys.exit(1)

        now = time.time()
        print(f"{INFO}Storing current database in temporary dump")
        tmp_db = f"tmp_migration_dump_{datetime.fromtimestamp(now).replace(microsecond=0).isoformat()}.json"
        StorageDump().run(
            name=tmp_db,
            dest_dir=".",
            description="automatically generated temporary migration dump",
            single=True,
            collections=None,
        )
        try:
            self.do_migration(ori_dump=tmp_db)
        except Exception:
            logger.exception("🔥 Oh no, something bad happened")
            sys.exit(1)
        else:
            print("\n🏁 All dumps and record are upgraded")
        finally:
            print(f"{INFO}Restoring original database")
            StorageRestore().run(
                keep_existing=False,
                archive=tmp_db,
            )
            Path(tmp_db).unlink()


superdesk.command("storage:dump", StorageDump())
superdesk.command("storage:restore", StorageRestore())
superdesk.command("storage:record", StorageStartRecording())
superdesk.command("storage:restore-record", StorageRestoreRecord())
superdesk.command("storage:list", StorageList())
superdesk.command("storage:upgrade-dumps", StorageMigrateDumps())
