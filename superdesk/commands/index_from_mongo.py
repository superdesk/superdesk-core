# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013 - 2015 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license
from eve.utils import ParsedRequest

import superdesk
import time
from superdesk.errors import BulkIndexError
from superdesk import config


class IndexFromMongo(superdesk.Command):
    """Index the specified mongo collection in the specified elastic collection/type.

    This will use the default APP mongo DB to read the data and the default Elastic APP index.
    """

    option_list = [
        superdesk.Option('--from', '-f', dest='mongo_collection_name', required=True),
        superdesk.Option('--page-size', '-p', dest='page_size')
    ]
    default_page_size = 500

    def run(self, mongo_collection_name, page_size):
        for items in self.get_mongo_items(mongo_collection_name, page_size):
            print('{} Inserting {} items'.format(time.strftime('%X %x %Z'), len(items)))
            s = time.time()

            for i in range(1, 4):
                try:
                    success, failed = superdesk.app.data._search_backend(mongo_collection_name).bulk_insert(
                        mongo_collection_name, items)
                except Exception as ex:
                    print('Exception thrown on insert to elastic {}', ex)
                    time.sleep(10)
                    continue
                else:
                    break

            print('{} Inserted {} items in {:.3f} seconds'.format(time.strftime('%X %x %Z'), success, time.time() - s))
            if failed:
                print('Failed to do bulk insert of items {}. Errors: {}'.format(len(failed), failed))
                raise BulkIndexError(resource=mongo_collection_name, errors=failed)

        return 'Finished indexing collection {}'.format(mongo_collection_name)

    def get_mongo_items(self, mongo_collection_name, page_size):
        """Generate list of items from given mongo collection per page size.

        :param mongo_collection_name: Name of the collection to get the items
        :param page_size: Size of every list in each iteration
        :return: list of items
        """
        bucket_size = int(page_size) if page_size else self.default_page_size
        print('Indexing data from mongo/{} to elastic/{}'.format(mongo_collection_name, mongo_collection_name))

        service = superdesk.get_resource_service(mongo_collection_name)
        req = ParsedRequest()
        req.sort = '[("%s", 1)]' % config.ID_FIELD
        cursor = service.get_from_mongo(req, {})
        count = cursor.count()
        no_of_buckets = len(range(0, count, bucket_size))
        water_mark = cursor[0][config.ID_FIELD]
        print('Number of items to index: {}, pages={}'.format(count, no_of_buckets))
        for x in range(0, no_of_buckets):
            print('{} Page : {}'.format(time.strftime('%X %x %Z'), x + 1))
            s = time.time()
            req = ParsedRequest()
            req.sort = '[("%s", 1)]' % config.ID_FIELD
            req.max_results = bucket_size
            if x == 0:
                lookup = {config.ID_FIELD: {'$gte': water_mark}}
            else:
                lookup = {config.ID_FIELD: {'$gt': water_mark}}

            cursor = service.get_from_mongo(req, lookup)
            items = list(cursor)
            water_mark = items[len(items) - 1][config.ID_FIELD]
            print('{} Retrieved from Mongo in {:.3f} seconds to {}'.format(time.strftime('%X %x %Z'), time.time() - s,
                  water_mark))

            yield items


superdesk.command('app:index_from_mongo', IndexFromMongo())
