# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


import requests
from urllib.parse import urljoin
import superdesk

from .index_from_mongo import IndexFromMongo


class FlushElasticIndex(superdesk.Command):
    """Flush elastic index.

    It removes elastic index, creates a new one and index it from mongo.
    You must specify at least one elastic index to flush:
    ``--sd`` (superdesk) or ``--capi`` (content api)
    """

    option_list = [
        superdesk.Option('--sd', action='store_true', dest='sd_index'),
        superdesk.Option('--capi', action='store_true', dest='capi_index')
    ]

    def run(self, sd_index, capi_index):
        if not (sd_index or capi_index):
            raise SystemExit('You must specify at least one elastic index to flush. '
                             'Options: `--sd`, `--capi`')
        if sd_index:
            self._flush_elastic(superdesk.app.config['ELASTICSEARCH_INDEX'])
        if capi_index:
            self._flush_elastic(superdesk.app.config['CONTENTAPI_ELASTICSEARCH_INDEX'])

        print('- Indexing all mongo collections into elastic index(s)')
        IndexFromMongo().run(
            collection_name=None,
            all_collections=True,
            page_size=IndexFromMongo.default_page_size
        )

    def _flush_elastic(self, index):
        es_index_url = urljoin(
            superdesk.app.config['ELASTICSEARCH_URL'],
            index
        )
        print('- Removing elastic index "{}"'.format(index))
        resp = requests.delete(es_index_url)
        if resp.status_code == requests.status_codes.codes.OK:
            print('\t- "{}" elastic index was deleted'.format(index))
        else:
            print(
                '\t- "{}" elastic index was not deleted. Server response: {}'.format(index, resp.text)
            )


superdesk.command('app:flush_elastic_index', FlushElasticIndex())
