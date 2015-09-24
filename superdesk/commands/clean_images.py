# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


import superdesk
from superdesk.storage.amazon.amazon_media_storage import AmazonMediaStorage


class CleanImages(superdesk.Command):
    """
    This command will remove all the images from the system which are not referenced by content.
    It checks the media type and calls the correspoinding function as s3 and mongo
    requires different approaches for handling multiple files.
    Probably running db.repairDatabase() is needed in Mongo to shring the DB size.
    """

    def run(self):
        try:
            print('Starting image cleaning.')
            used_images = set()

            archive_items = superdesk.get_resource_service('archive').get_from_mongo(None, {'type': 'picture'})
            self.__add_existing_files(used_images, archive_items)

            ingest_items = superdesk.get_resource_service('ingest').get_from_mongo(None, {'type': 'picture'})
            self.__add_existing_files(used_images, ingest_items)

            upload_items = superdesk.get_resource_service('upload').get_from_mongo(req=None, lookup={})
            self.__add_existing_files(used_images, upload_items)

            print('Number of used files: ', len(used_images))

            if isinstance(superdesk.app.media, AmazonMediaStorage):
                self._compare_s3_files(used_images)
            else:
                self._compare_gridfs_files(used_images)

        except Exception as ex:
            print(ex)

    def __add_existing_files(self, used_images, items):
        for item in items:
            if 'media' in item:
                used_images.add(str(item['media']))

            for file_id in [str(rend.get('media')) for rend in item.get('renditions', {}).values()
                            if rend.get('media')]:
                used_images.add(file_id)

    def _compare_gridfs_files(self, used_images):
        """ Gets the files from Grid FS and compars agains used images and deletes the orphans """
        current_files = superdesk.app.media.fs('upload').find({'_id': {'$nin': list(used_images)}})
        for file_id in (file._id for file in current_files if str(file._id) not in used_images):
            print('Removing unused file: ', file_id)
            superdesk.app.media.delete(file_id)
        print('Image cleaning completed successfully.')

    def _compare_s3_files(self, used_images):
        """ Gets the files from S3 and compars agains used images and deletes the orphans """
        bucket_files = superdesk.app.media.get_all_keys()
        orphan_files = list(set(bucket_files) - used_images)
        print('There are {} orphan files...'.format(len(orphan_files)))

        if len(orphan_files) > 0:
            print('Cleaning the orphan files...')
            deleted, errors = superdesk.app.media.delete_objects(orphan_files)
            if deleted:
                print('Image cleaning completed successfully.')
            else:
                print('Failed to clean orphans: {}'.format(errors))
        else:
            print('There\'s nothing to clean.')


superdesk.command('app:clean_images', CleanImages())
