# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013 - 2015 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import time
import pymongo
import superdesk

from superdesk.resource_fields import ID_FIELD
from superdesk.errors import BulkIndexError
from bson.objectid import ObjectId

from superdesk.core import get_current_async_app


class IndexFromMongo(superdesk.Command):
    """Index the specified mongo collection in the specified elastic collection/type.

    This will use the default APP mongo DB to read the data and the default Elastic APP index.

    Use ``-f all`` to index all collections.

    Example:
    ::

        $ python manage.py app:index_from_mongo --from=archive
        $ python manage.py app:index_from_mongo --all

    """

    option_list = [
        # superdesk.Option("--from", "-f", dest="collection_name"),
        # superdesk.Option("--all", action="store_true", dest="all_collections"),
        # superdesk.Option("--page-size", "-p"),
        # superdesk.Option("--last-id"),
        # superdesk.Option("--string-id", dest="string_id", action="store_true", help="Treat the id's as strings"),
    ]
    default_page_size = 500

    async def run(self, collection_name, all_collections, page_size, last_id, string_id):
        if not collection_name and not all_collections:
            raise SystemExit("Specify --all to index from all collections")
        elif all_collections:
            async_app = get_current_async_app()
            app = async_app.wsgi
            await app.data.init_elastic(app)
            resources = app.data.get_elastic_resources()
            resources_processed = []
            for resource_config in async_app.resources.get_all_configs():
                if resource_config.elastic is None:
                    continue
                self.copy_resource(resource_config.name, page_size)
                resources_processed.append(resource_config.name)

            for resource in resources:
                if resource in resources_processed:
                    # This resource has already been processed by the new app
                    # No need to re-index this resource
                    continue
                self.copy_resource(resource, page_size)
        else:
            self.copy_resource(collection_name, page_size, last_id, string_id)

    @classmethod
    def copy_resource(cls, resource, page_size, last_id=None, string_id=False):
        async_app = get_current_async_app()
        for items in cls.get_mongo_items(resource, page_size, last_id, string_id):
            print("{} Inserting {} items".format(time.strftime("%X %x %Z"), len(items)))
            s = time.time()
            success, failed = 0, 0

            for i in range(1, 4):
                try:
                    try:
                        success, failed = async_app.elastic.get_client(resource).bulk_insert(items)
                    except KeyError:
                        app = async_app.wsgi
                        success, failed = app.data._search_backend(resource).bulk_insert(resource, items)
                except Exception as ex:
                    print("Exception thrown on insert to elastic {}", ex)
                    time.sleep(10)
                    continue
                else:
                    break

            print("{} Inserted {} items in {:.3f} seconds".format(time.strftime("%X %x %Z"), success, time.time() - s))

            if failed:
                print("Failed to do bulk insert of items {}. Errors: {}".format(len(failed), failed))
                raise BulkIndexError(resource=resource, errors=failed)

        return "Finished indexing collection {}".format(resource)

    @classmethod
    def get_mongo_items(cls, mongo_collection_name, page_size, last_id, string_id):
        """Generate list of items from given mongo collection per page size.

        :param mongo_collection_name: Name of the collection to get the items
        :param page_size: Size of every list in each iteration
        :return: list of items
        """
        bucket_size = int(page_size) if page_size else cls.default_page_size
        print("Indexing data from mongo/{} to elastic/{}".format(mongo_collection_name, mongo_collection_name))
        async_app = get_current_async_app()

        try:
            db = async_app.mongo.get_collection(mongo_collection_name)
        except KeyError:
            app = async_app.wsgi
            db = app.data.get_mongo_collection(mongo_collection_name)

        args = {"limit": bucket_size, "sort": [(ID_FIELD, pymongo.ASCENDING)]}

        while True:
            if last_id:
                if not string_id:
                    try:
                        last_id = ObjectId(last_id)
                    except Exception:
                        pass
                args.update({"filter": {ID_FIELD: {"$gt": last_id}}})

            cursor = db.find(**args)
            items = list(cursor)
            if not len(items):
                print("Last id", mongo_collection_name, last_id)
                break
            last_id = items[-1][ID_FIELD]
            yield items


superdesk.command("app:index_from_mongo", IndexFromMongo())
