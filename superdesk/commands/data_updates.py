# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from functools import wraps
import os
import re
import time
import click
import getpass
import superdesk

from string import Template
from types import ModuleType
from typing import Literal, Optional, Tuple
from inspect import iscoroutinefunction

from pymongo.database import Database, Collection
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection

from eve.utils import ParsedRequest

from superdesk.core.app import get_current_async_app
from superdesk.services import BaseService
from superdesk.core import get_app_config, get_current_app

from .async_cli import cli


DEFAULT_DATA_UPDATE_DIR_NAME = "data_updates"
MAIN_DATA_UPDATES_DIR = os.path.abspath(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, DEFAULT_DATA_UPDATE_DIR_NAME)
)
DATA_UPDATES_FILENAME_REGEX = re.compile("^(\d+).*\.py$")
DATA_UPDATE_TEMPLATE = """
# -*- coding: utf-8; -*-
# This file is part of Superdesk.
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license
#
# Author  : $user
# Creation: $current_date

from superdesk.commands.data_updates import BaseDataUpdate


class DataUpdate(BaseDataUpdate):

    resource = '$resource'

    def forwards(self, mongodb_collection, mongodb_database):
        $default_fw_implementation

    def backwards(self, mongodb_collection, mongodb_database):
        $default_bw_implementation
""".lstrip(
    "\n"
)
DEFAULT_DATA_UPDATE_FW_IMPLEMENTATION = "raise NotImplementedError()"
DEFAULT_DATA_UPDATE_BW_IMPLEMENTATION = "raise NotImplementedError()"


def get_dirs(only_relative_folder=False):
    dirs = []
    try:
        dirs.append(get_app_config("DATA_UPDATES_PATH", DEFAULT_DATA_UPDATE_DIR_NAME))
        if get_app_config("APPS_DATA_UPDATES_PATHS"):
            dirs.extend(get_app_config("APPS_DATA_UPDATES_PATHS"))
    except RuntimeError:
        # working outside of application context
        pass
    if not only_relative_folder:
        dirs.append(MAIN_DATA_UPDATES_DIR)
    assert len(dirs)
    return dirs


def get_data_updates_files(strip_file_extension=False):
    """Return the list of data updates filenames.

    .py extension can be removed with `strip_file_extension` parameter.
    """
    files = []
    # create folder if doens't exist
    for folder in get_dirs():
        if not os.path.exists(folder):
            continue
        # list all files from data updates directory
        if os.path.exists(folder):
            files += [f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))]
    # keep only data updates (00000x*.py)
    files = [f for f in files if DATA_UPDATES_FILENAME_REGEX.match(f)]
    # order file names
    files = sorted(files)
    # remove .py extention if needed
    if strip_file_extension:
        files = [f.rstrip(".py") for f in files]
    return files


def get_applied_updates(data_updates_service: Optional[BaseService] = None) -> Tuple[str]:
    if data_updates_service is None:
        data_updates_service = superdesk.get_resource_service("data_updates")
    req = ParsedRequest()
    req.sort = "-name"
    return tuple(data_updates_service.get(req=req, lookup={}))  # type: ignore


async def initialize_data_updates(fake, dry):
    data_updates_service = superdesk.get_resource_service("data_updates")
    data_updates_files = get_data_updates_files(strip_file_extension=True)
    data_updates_applied = get_applied_updates(data_updates_service)
    last_data_update = data_updates_applied and data_updates_applied[-1] or None

    if last_data_update and last_data_update["name"] not in data_updates_files:
        print(
            "A data update previously applied to this database (%s) can't be found in %s"
            % (last_data_update["name"], ", ".join(get_dirs()))
        )
    return data_updates_service, data_updates_files, last_data_update


def compile_update_in_module(data_update_name):
    date_update_script_file = None
    for folder in get_dirs():
        date_update_script_file = os.path.join(folder, "%s.py" % (data_update_name))
        if os.path.exists(date_update_script_file):
            break
    assert date_update_script_file is not None, "File %s has not been found" % (data_update_name)

    # create a module instance to use as scope for our data update
    module = ModuleType("data_update_module")
    with open(date_update_script_file) as f:
        # compile data update script file
        script = compile(f.read(), date_update_script_file, "exec")
        # excecute the script in the module
        exec(script, module.__dict__)

    return module


def in_db(update, data_updates_service):
    applied_updates = get_applied_updates(data_updates_service)
    return update in map(lambda _: _["name"], applied_updates)


def common_options(func):
    @click.option("--data-update-id", "-i", type=str, required=False, help="Data update id to run last")
    @click.option("--fake-init", "fake", is_flag=True, help="Mark data updates as run without actually running them")
    @click.option(
        "--dry-run", "dry", is_flag=True, help="Does not mark data updates as done. This can be useful for development."
    )
    @wraps(func)
    async def wrapper(*args, **kwargs):
        return await func(*args, **kwargs)

    return wrapper


@cli.register_async_command("data:upgrade", with_appcontext=True)
@common_options
async def upgrade_command(*args, **kwargs):
    """Runs all the new data updates available.

    If ``data_update_id`` is given, runs new data updates until the given one.

    Example:
    ::

        $ python manage.py data:upgrade

    """
    return await upgrade_command_handler(*args, **kwargs)


async def upgrade_command_handler(data_update_id=None, fake=False, dry=False):
    data_updates_service, data_updates_files, _ = await initialize_data_updates(fake, dry)

    if data_update_id and data_update_id not in data_updates_files:
        print(
            "Error argument --id/-i: invalid choice: '{}' (choose from  {})".format(data_update_id, data_updates_files)
        )
        return

    # Filter and apply updates
    data_updates_files = [update for update in data_updates_files if not in_db(update, data_updates_service)]
    if data_update_id:
        if data_update_id not in data_updates_files:
            print("Given data update id not found in available updates. It may have been already applied")
            return False
        data_updates_files = data_updates_files[: data_updates_files.index(data_update_id) + 1]

    # apply data updates
    for data_update_name in data_updates_files:
        print(f"data update {data_update_name} running forward...")
        module_scope = compile_update_in_module(data_update_name)
        if not fake:
            module_scope.DataUpdate().apply("forwards")
        if not dry:
            data_updates_service.create([{"name": data_update_name}])

    if not data_updates_files:
        print("No data update to apply.")


@cli.register_async_command("data:downgrade", with_appcontext=True)
@common_options
async def downgrade_command(*args, **kwargs):
    """Runs the latest data update backward.

    If ``data_update_id`` is given, runs all the data updates backward until the given one.

    Example:
    ::

        $ python manage.py data:downgrade

    """

    return await downgrade_command_handler(*args, **kwargs)


async def downgrade_command_handler(data_update_id=None, fake=False, dry=False):
    data_updates_service, data_updates_files, last_data_update = await initialize_data_updates(fake, dry)

    if data_update_id and data_update_id not in data_updates_files:
        print(
            "Error argument --id/-i: invalid choice: '{}'"
            " (choose from  {})".format(data_update_id, get_data_updates_files(strip_file_extension=True))
        )
        return

    # check if there is something to downgrade
    if not last_data_update:
        print("No data update has been already applied")
        return False

    # drops updates which have not been already made (this is rollback mode)
    data_updates_files = [update for update in data_updates_files if in_db(update, data_updates_service)]

    # if data_update_id is given, go until this update (drop previous updates)
    if data_update_id:
        if data_update_id not in data_updates_files:
            print(f"Update {data_update_id} can't be find. It may have been already downgraded")
            return False
        data_updates_files = data_updates_files[data_updates_files.index(data_update_id) :]
    # otherwise, just rollback one update
    else:
        print(f"No data update id has been provided. Dowgrading to previous version: {last_data_update['name']}")
        data_updates_files = data_updates_files[len(data_updates_files) - 1 :]

    # apply data updates, in the opposite direction
    for data_update_name in reversed(data_updates_files):
        print(f"data update {data_update_name} running backward...")
        module_scope = compile_update_in_module(data_update_name)
        # run the data update backward
        if not fake:
            module_scope.DataUpdate().apply("backwards")
        if not dry:
            # remove the applied data update from the database
            data_updates_service.delete({"name": data_update_name})
    if not data_updates_files:
        print("No data update to apply.")


class GenerateUpdate(superdesk.Command):
    """Generate a file where to define a new data update.

    Example:
    ::

        $ python manage.py data:generate_update --resource=archive

    """

    option_list = [
        # superdesk.Option("--resource", "-r", dest="resource_name", required=True, help="Resource to update"),
        # superdesk.Option(
        #     "--global",
        #     "-g",
        #     dest="global_update",
        #     required=False,
        #     action="store_true",
        #     help="This data update belongs to superdesk core",
        # ),
    ]

    def run(self, resource_name, global_update=False):
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        # create a data update file
        try:
            last_file = get_data_updates_files()[-1]
            name_id = int(last_file.replace(".py", "").split("_")[0]) + 1
        except IndexError:
            name_id = 0
        if global_update:
            update_dir = MAIN_DATA_UPDATES_DIR
        else:
            update_dir = get_dirs(only_relative_folder=True)[0]
        if not os.path.exists(update_dir):
            os.makedirs(update_dir)
        data_update_filename = os.path.join(update_dir, "{:05d}_{}_{}.py".format(name_id, timestamp, resource_name))
        if os.path.exists(data_update_filename):
            raise Exception('The file "%s" already exists' % (data_update_filename))
        with open(data_update_filename, "w+") as f:
            template_context = {
                "resource": resource_name,
                "current_date": time.strftime("%Y-%m-%d %H:%M"),
                "user": getpass.getuser(),
                "default_fw_implementation": DEFAULT_DATA_UPDATE_FW_IMPLEMENTATION,
                "default_bw_implementation": DEFAULT_DATA_UPDATE_BW_IMPLEMENTATION,
            }
            f.write(Template(DATA_UPDATE_TEMPLATE).substitute(template_context))
            print("Data update file created %s" % (data_update_filename))


superdesk.command("data:generate_update", GenerateUpdate())


def get_db_and_collection(
    resource_name: str, is_async: bool = True
) -> Tuple[AsyncIOMotorCollection, AsyncIOMotorDatabase] | Tuple[Collection, Database]:
    """
    Retrieves the appropriate collection and database based on the `is_async` flag.

    Args:
        resource_name: The name of the resource (collection).
        is_async: Boolean flag indicating whether the operation is asynchronous or synchronous.

    Returns:
        Tuple of collection and database corresponding to async or sync versions.
    """

    async_app = get_current_async_app()
    app = async_app.wsgi

    if is_async:
        collection = async_app.mongo.get_collection_async(resource_name)
        db = async_app.mongo.get_db_async(resource_name)
    else:
        collection = app.data.get_mongo_collection(resource_name)
        db = app.data.driver.db

    return collection, db


class BaseDataUpdate:
    resource: str

    async def apply(self, direction: Literal["forwards", "backwards"]):
        """
        Applies a data update depending on the direction, either asynchronous or synchronous.

        Args:
            direction (str): The direction of the update, either 'forwards' or 'backwards'.

        Raises:
            AssertionError: If the direction is not 'forwards' or 'backwards'.
        """

        assert direction in ["forwards", "backwards"]
        direction_func = getattr(self, direction)

        is_async = iscoroutinefunction(direction_func)
        collection, db = get_db_and_collection(self.resource, is_async)

        if is_async:
            await direction_func(collection, db)
        else:
            direction_func(collection, db)


DataUpdate = BaseDataUpdate
