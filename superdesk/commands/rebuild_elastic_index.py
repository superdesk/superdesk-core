# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import click

from superdesk.core import get_current_async_app

from .async_cli import cli


@cli.command("app:rebuild_elastic_index")
@click.option("--resource", "-r", "resource_name")
@click.option("--requests-per-second", "requests_per_second", type=int, default=1000)
def cli_rebuild_elastic_index(resource_name, requests_per_second):
    """Rebuild the elastic indexes from existing data.

    It creates new index with same alias as the configured index,
    puts the new mapping and removes the old index.

    Example:
    ::

        $ python manage.py app:rebuild_elastic_index
        $ python manage.py app:rebuild_elastic_index --resource=items
        $ python manage.py app:rebuild_elastic_index --resource=archive

    """

    RebuildElasticIndex().run(resource_name, requests_per_second)


class RebuildElasticIndex:
    def run(self, resource_name=None, requests_per_second=1000):
        # if no index name is passed then use the configured one
        async_app = get_current_async_app()
        app = async_app.wsgi
        resources = list(app.data.elastic._get_elastic_resources().keys())
        async_resource_configs = async_app.resources.get_all_configs()
        async_resources = {config.name for config in async_resource_configs}
        if resource_name and (resource_name in resources or resource_name in async_resources):
            resources = [resource_name]
        elif resource_name:
            raise ValueError("Resource {} is not configured".format(resource_name))

        resources_processed = []
        for config in async_resource_configs:
            if config.elastic is None or not config.elastic.auto_create_index:
                continue
            async_app.elastic.reindex(config.name, requests_per_second=requests_per_second)
            resources_processed.append(config.name)
            print(f"Index {config.name} rebuilt successfully")

        for resource in resources:
            if resource in resources_processed:
                # This resource has already been processed by the new app
                # No need to rebuilt its index
                continue
            app.data.elastic.reindex(resource, requests_per_second=requests_per_second)
            print('Index {} rebuilt successfully.'.format(resource))
