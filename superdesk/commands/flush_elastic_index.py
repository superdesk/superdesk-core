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

from eve_elastic import get_es
from elasticsearch import exceptions as es_exceptions

from superdesk.commands import cli
from superdesk.core import get_app_config, get_current_app, get_current_async_app
from content_api import ELASTIC_PREFIX as CAPI_ELASTIC_PREFIX

from .index_from_mongo import IndexFromMongo

# this one is not configurable
SD_ELASTIC_PREFIX = "ELASTICSEARCH"


class FlushElasticIndex:
    """Flush elastic index.

    It removes elastic index, creates a new one and index it from mongo.
    You must specify at least one elastic index to flush:
    ``--sd`` (superdesk) or ``--capi`` (content api)

    Example:
    ::

        $ python manage.py app:flush_elastic_index --sd
        $ python manage.py app:flush_elastic_index --capi
        $ python manage.py app:flush_elastic_index --sd --capi

    """

    async def run(self, sd_index: bool, capi_index: bool):
        if not (sd_index or capi_index):
            raise SystemExit("You must specify at least one elastic index to flush. " "Options: `--sd`, `--capi`")

        self._es = get_es(get_app_config("ELASTICSEARCH_URL"))

        elastic_index_prefix = get_app_config("ELASTICSEARCH_INDEX")
        content_api_index_prefix = get_app_config("CONTENTAPI_ELASTICSEARCH_INDEX")

        if sd_index:
            self._delete_elastic(elastic_index_prefix)

        # delete content_api's index if it's not the same as default one
        if capi_index and elastic_index_prefix != content_api_index_prefix:
            self._delete_elastic(content_api_index_prefix)

        self._delete_indices_from_async_resources()

        await self._index_from_mongo(sd_index, capi_index)
        await self._index_from_mongo_async_resources()

    def _delete_elastic(self, index_prefix):
        """Deletes elastic indices with `index_prefix`

        :param str index_prefix: elastix index
        :raise: SystemExit exception if delete elastic index response status is not 200 or 404.
        """

        indices = list(self._es.indices.get_alias("{}_*".format(index_prefix)).keys())
        print(f"Configured indices with prefix '{index_prefix}': " + ", ".join(indices))

        app = get_current_app()
        for es_resource in app.data.get_elastic_resources():
            alias = app.data.elastic._resource_index(es_resource)
            print(f"- Attempting to delete alias {alias}")
            for index in indices:
                if index.rsplit("_", 1)[0] == alias or index == alias:
                    try:
                        print('- Removing elastic index "{}"'.format(index))
                        self._es.indices.delete(index=index)
                    except es_exceptions.NotFoundError:
                        print('\t- "{}" elastic index was not found. Continue without deleting.'.format(index))
                    except es_exceptions.TransportError as e:
                        raise SystemExit(
                            '\t- "{}" elastic index was not deleted. Exception: "{}"'.format(index, e.error)
                        )
                    else:
                        print('\t- "{}" elastic index was deleted.'.format(index))
                        break

    async def _index_from_mongo(self, sd_index: bool, capi_index: bool):
        """Index elastic search from mongo.

        if `sd_index` is true only superdesk elastic index will be indexed.
        if `capi_index` is true only content api elastic index will be indexed.

        :param bool sd_index: Flag to index superdesk elastic index.
        :param bool capi_index: Flag to index content api elastic index.
        """
        # get all es resources
        app = get_current_app()
        await app.data.init_elastic(app)
        resources = app.data.get_elastic_resources()

        for resource in resources:
            # get es prefix per resource
            es_backend = app.data._search_backend(resource)
            resource_es_prefix = es_backend._resource_prefix(resource)

            if resource_es_prefix == SD_ELASTIC_PREFIX and sd_index:
                print(f'Indexing mongo collections into "{app.config["ELASTICSEARCH_INDEX"]}" elastic index.')
                IndexFromMongo.copy_resource(resource, IndexFromMongo.default_page_size)

            if resource_es_prefix == CAPI_ELASTIC_PREFIX and capi_index:
                print(
                    f'Indexing mongo collections into "{app.config["CONTENTAPI_ELASTICSEARCH_INDEX"]}" elastic index.'
                )
                IndexFromMongo.copy_resource(resource, IndexFromMongo.default_page_size)

    def _delete_indices_from_async_resources(self):
        """
        Delete the elastic indices for the registered async resources
        """
        async_app = get_current_async_app()
        async_app.elastic.drop_indexes()

    async def _index_from_mongo_async_resources(self):
        """
        Index into elastic search from mongo async resources
        """
        async_app = get_current_async_app()
        for config in async_app.resources.get_all_configs():
            if config.elastic is None:
                continue

            IndexFromMongo.copy_resource(config.name, IndexFromMongo.default_page_size)


@cli.register_async_command("app:flush_elastic_index", with_appcontext=True)
@click.option("--sd", "sd_index", is_flag=True, help="To flush only superdesk index")
@click.option("--capi", "capi_index", is_flag=True, help="To flush only content api index")
async def flush_elastic_index_command(*args, **kwargs):
    """
    Flush elastic index.

    It removes elastic index, creates a new one and index it from mongo.
    You must specify at least one elastic index to flush:
    ``--sd`` (superdesk) or ``--capi`` (content api)
    """

    return await FlushElasticIndex().run(*args, **kwargs)
