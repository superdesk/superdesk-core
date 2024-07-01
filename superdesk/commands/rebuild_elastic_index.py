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

from flask import current_app as app
from superdesk.core.app import get_current_app


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
        superdesk.Option('--resource', '-r', dest='resource_name'),
        superdesk.Option('--requests-per-second', dest='requests_per_second'),
    ]

    def run(self, resource_name=None, requests_per_second=1000):
        # if no index name is passed then use the configured one
        resources = list(app.data.elastic._get_elastic_resources().keys())
        if resource_name and resource_name in resources:
            resources = [resource_name]
        elif resource_name:
            raise ValueError("Resource {} is not configured".format(resource_name))

        resources_processed = []
        new_app = get_current_app()
        for config in new_app.resources.get_all_configs():
            if config.elastic is None:
                continue
            new_app.elastic.reindex(config.name, requests_per_second=requests_per_second)
            resources_processed.append(config.name)
            print(f"Index {config.name} rebuilt successfully")

        for resource in resources:
            if resource in resources_processed:
                # This resource has already been processed by the new app
                # No need to rebuilt its index
                continue
            app.data.elastic.reindex(resource, requests_per_second=requests_per_second)
            print('Index {} rebuilt successfully.'.format(resource))


superdesk.command('app:rebuild_elastic_index', RebuildElasticIndex())
