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
import elasticsearch

from superdesk.utils import get_random_string
from eve_elastic import get_es, get_indices, reindex
from apps.search import SearchService


class RebuildElasticIndex(superdesk.Command):
    """Rebuild the elastic index from existing data.

    It is creating a new index with the same alias as the configured index,
    puts the new mapping and delete the old index.
    """

    option_list = [
        superdesk.Option('--index', '-i', dest='index_name')
    ]

    def run(self, index_name=None):
        # if no index name is passed then use the configured one
        index_name = index_name if index_name else superdesk.app.config['ELASTICSEARCH_INDEX']
        print('Starting index rebuilding for index: {}'.format(index_name))
        if index_name not in self._get_available_indexes():
            raise Exception("Index {} is not configured".format(index_name))
        try:
            es = get_es(superdesk.app.config['ELASTICSEARCH_URL'])
            clone_name = index_name + '-' + get_random_string()
            print('Creating index: ', clone_name)
            superdesk.app.data.elastic.create_index(clone_name, superdesk.app.config['ELASTICSEARCH_SETTINGS'])
            real_name = superdesk.app.data.elastic.get_index_by_alias(clone_name)
            print('Putting mapping for index: ', clone_name)
            superdesk.app.data.elastic.put_mapping(superdesk.app, clone_name)
            print('Starting index rebuilding.')
            reindex(es, index_name, clone_name)
            print('Finished index rebuilding.')
            print('Deleting index: ', index_name)
            get_indices(es).delete(index_name)
            print('Creating alias: ', index_name)
            get_indices(es).put_alias(index=real_name, name=index_name)
            print('Alias created.')
            print('Deleting clone name alias')
            get_indices(es).delete_alias(name=clone_name, index=real_name)
            print('Deleted clone name alias')
        except elasticsearch.exceptions.NotFoundError as nfe:
            print(nfe)
        print('Index {0} rebuilt successfully.'.format(index_name))

    def _get_available_indexes(self):
        return SearchService(None, None).get_available_indexes()


superdesk.command('app:rebuild_elastic_index', RebuildElasticIndex())
