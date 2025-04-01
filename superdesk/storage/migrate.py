import codecs
import click

from superdesk.commands import cli
from superdesk.core import get_current_app


@cli.command("media:migrate")
@click.option("--limit", "-l", required=False, default=50, type=int)
@click.option("--skip", "-s", required=False, default=0, type=int)
@click.option("--delete", "-d", required=False, default=False, is_flag=True)
def cli_media_migrate(limit, skip, delete):
    """Migrate media files from Mongo GridFS to Amazon S3.

    Usage::

        $ python manage.py media:migrate
        $ python manage.py media:migrate --limit 100
        $ python manage.py media:migrate --limit 100 --skip 100
        $ python manage.py media:migrate --limit 100 --skip 100 --delete

    Options:

    -l, --limit  Number of files to migrate.
    -s, --skip   Number of files to skip.
    -d, --delete Delete files from Mongo GridFS after migration.
    """

    MigrateMediaCommand().run(limit, skip, delete)


class MigrateMediaCommand:
    def run(self, limit, skip, delete):
        app = get_current_app()
        mongo = app.media._storage[1]
        amazon = app.media._storage[0]

        files = mongo.fs().find(no_cursor_timeout=True).limit(limit).skip(skip)
        if not files.count():
            print("There are no files in mongo to be migrated.")
            return

        print("starting to migrate {} files".format(files.count()))
        migrated = 0

        for file in files:
            try:
                saved = amazon.put(
                    file.read(),
                    filename=file.filename,
                    content_type=file.content_type,
                    metadata=file.metadata,
                    _id=str(file._id),
                    ContentMD5=codecs.encode(codecs.decode(file.md5, "hex"), "base64").decode().strip(),
                )
                if saved:
                    if delete:
                        mongo.delete(file._id)
                    migrated += 1
                    print(".", end="")
            except Exception as error:
                print("Error while migrating file {}: {}".format(file._id, error))

        print("done migrating {} files.".format(migrated))
