
import codecs
import superdesk

from flask import current_app as app


class MigrateMediaCommand(superdesk.Command):
    """It will migrate files from Mongo GridFS into Amazon S3 storage."""

    option_list = [
        superdesk.Option('--limit', '-l', dest='limit', required=False, default=50, type=int)
    ]

    def run(self, limit):
        mongo = app.media._storage[0]
        amazon = app.media._storage[1]

        files = mongo.fs().find()
        print("starting to migrate {}/{} files".format(limit, files.count()))

        counter = 0
        for file in files:
            amazon.put(
                file.read(),
                filename=file.filename,
                content_type=file.content_type,
                metadata=file.metadata,
                _id=str(file._id),
                ContentMD5=codecs.encode(codecs.decode(file.md5, 'hex'), 'base64').decode().strip(),
            )
            mongo.delete(file._id)
            counter += 1
            if counter == limit:
                break

        print('done migrating {} files.'.format(counter))


superdesk.command('media:migrate', MigrateMediaCommand())
