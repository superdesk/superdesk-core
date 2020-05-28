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

from flask import current_app
from eve_elastic import get_es, get_indices, reindex
from superdesk.utils import get_random_string


class RebuildElasticIndex(superdesk.Command):
    """Rebuild the elastic indexes from existing data.

    It creates new index with same alias as the configured index,
    puts the new mapping and removes the old index.

    Example:
    ::

        $ python manage.py app:rebuild_elastic_index
        $ python manage.py app:rebuild_elastic_index --resource=items
        $ python manage.py app:rebuild_elastic_index --resource=archive

    """

    option_list = [
        superdesk.Option('--resource', '-r', dest='resource_name')
    ]

    def run(self, resource_name=None):
        # if no index name is passed then use the configured one
        resources = list(current_app.data.elastic._get_elastic_resources().keys())
        if resource_name and resource_name in resources:
            resources = [resource_name]
        elif resource_name:
            raise ValueError("Resource {} is not configured".format(resource_name))
        for resource in resources:
            try:
                current_app.data.elastic.reindex(resource)
            except elasticsearch.exceptions.NotFoundError as nfe:
                print(nfe)
            print('Index {} rebuilt successfully.'.format(resource_name))


superdesk.command('app:rebuild_elastic_index', RebuildElasticIndex())
