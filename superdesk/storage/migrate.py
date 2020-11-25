import codecs
import superdesk

from flask import current_app as app


class MigrateMediaCommand(superdesk.Command):
    """It will migrate files from Mongo GridFS into Amazon S3 storage."""

    option_list = [
        superdesk.Option("--limit", "-l", dest="limit", required=False, default=50, type=int),
        superdesk.Option("--skip", "-s", dest="skip", required=False, default=0, type=int),
    ]

    def run(self, limit, skip):
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
                    mongo.delete(file._id)
                    migrated += 1
                    print(".", end="")
            except Exception as error:
                print("Error while migrating file {}: {}".format(file._id, error))

        print("done migrating {} files.".format(migrated))


superdesk.command("media:migrate", MigrateMediaCommand())
