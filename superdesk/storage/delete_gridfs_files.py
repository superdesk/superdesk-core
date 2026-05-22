from typing import cast
from datetime import datetime

from bson import ObjectId
from gridfs import GridFS, GridOut
import click

from superdesk.core import get_current_app
from superdesk.commands import cli
from .proxy import ProxyMediaStorage
from .desk_media_storage import SuperdeskGridFSMediaStorage


@cli.command("storage:delete_gridfs_files")
@click.option("--to", "-t", required=True, type=str, help="End date for file deletion")
@click.option(
    "--content-type", "-c", "content_types", multiple=True, type=str, help="Delete files with this ContentType"
)
@click.option("--limit", "-l", type=int, default=50)
@click.option("--iterations", "-i", type=int, default=10)
@click.option("--dry-run", "-d", is_flag=True)
def cli_delete_gridfs_files(to: str, content_types: list[str], limit: int, iterations: int, dry_run: bool) -> None:
    """Delete files from MongoDB GridFS based on provided arguments.

    Arguments:
    - `-t`, `--to`: End date for file deletion
    - `-c`, `--content-type`: Optional list of content types to filter files
    - `-l`, `--limit`: Maximum number of files to process per batch
    - `-i`, `--iterations`: Maximum number of iterations to process
    - `-d`, `--dry-run`: Simulate the deletion process without actually removing the files

    Example:
    ::

        python manage.py storage:delete_gridfs_files --to="2024-01-01T12:00:00"
        python manage.py storage:delete_gridfs_files --to="2024-01-01T12:00:00" -c "video/mp4" -c "image/png"

    """
    to_date = datetime.fromisoformat(to)
    query: dict = {"uploadDate": {"$lte": to_date}}
    if content_types:
        query["contentType"] = {"$in": content_types}

    files_deleted = _delete_files_in_batches(query, limit, iterations, dry_run)
    print(f"Done. Deleted {files_deleted} files")


def _delete_files_in_batches(query: dict, limit: int, iterations: int, dry_run: bool) -> int:
    client = _get_gridfs_client()
    total_file_count = client._files.count_documents(query)

    print(f"Found {total_file_count} GridFS files to delete.")

    if total_file_count == 0:
        return 0

    last_id: ObjectId | None = None
    files_deleted = 0

    for _ in range(iterations):
        lookup = query.copy()
        if last_id is not None:
            lookup["_id"] = {"$gt": last_id}

        file_batch = list(client.find(lookup).sort("_id").limit(limit))
        if not file_batch:
            break

        print(f"Deleting {len(file_batch)} files: ", end="\n" if dry_run else "", flush=True)
        for file in file_batch:
            if _delete_file(client, file, dry_run):
                files_deleted += 1

            last_id = file._id

        if not dry_run:
            print("")
    else:
        print("Max iterations reached, not all files were deleted!")

    return files_deleted


def _delete_file(client: GridFS, file: GridOut, dry_run: bool) -> bool:
    if dry_run:
        print(f"MOCK: deleting file '{file.filename}' ({file._id})")
        return True

    try:
        client.delete(file._id)
        print(".", end="", flush=True)
        return True
    except Exception as error:
        print(f"Error deleting file {file._id}: {error}")
        return False


def _get_gridfs_client() -> GridFS:
    app = get_current_app()
    storages = app.media._storage if isinstance(app.media, ProxyMediaStorage) else [app.media]
    for storage in storages:
        if isinstance(storage, SuperdeskGridFSMediaStorage):
            return cast(GridFS, storage.fs())
    raise RuntimeError("Unable to find GridFS storage")
