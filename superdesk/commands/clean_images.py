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


class CleanImages(superdesk.Command):
    """This command will remove all the images from the system which are not referenced by content.

    It checks the media type and calls the correspoinding function as s3 and mongo
    requires different approaches for handling multiple files.
    Probably running db.repairDatabase() is needed in Mongo to shring the DB size.
    """

    def run(self):
        try:
            print('Starting image cleaning.')
            used_images = set()
            types = ['picture', 'video', 'audio']

            archive_items = superdesk.get_resource_service('archive').get_from_mongo(None, {'type': {'$in': types}})
            self.__add_existing_files(used_images, archive_items)

            ingest_items = superdesk.get_resource_service('ingest').get_from_mongo(None, {'type': {'$in': types}})
            self.__add_existing_files(used_images, ingest_items)

            upload_items = superdesk.get_resource_service('upload').get_from_mongo(req=None, lookup={})
            self.__add_existing_files(used_images, upload_items)

            legal_archive_items = superdesk.get_resource_service('legal_archive').\
                get_from_mongo(None, {'type': {'$in': types}})
            self.__add_existing_files(used_images, legal_archive_items)

            legal_archive_version_items = superdesk.get_resource_service('legal_archive_versions').\
                get_from_mongo(None, {'type': {'$in': types}})
            self.__add_existing_files(used_images, legal_archive_version_items)

            print('Number of used files: ', len(used_images))

            superdesk.app.media.remove_unreferenced_files(used_images)

        except Exception as ex:
            print(ex)

    def __add_existing_files(self, used_images, items):
        for item in items:
            if 'media' in item:
                used_images.add(str(item['media']))

            for file_id in [str(rend.get('media')) for rend in item.get('renditions', {}).values()
                            if rend.get('media')]:
                used_images.add(file_id)


superdesk.command('app:clean_images', CleanImages())
