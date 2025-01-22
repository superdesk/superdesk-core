# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from typing import cast
import click

from eve_elastic import get_es
from elasticsearch import exceptions as es_exceptions

from superdesk.commands import cli
from superdesk.core import get_app_config, get_current_app, get_current_async_app

from .index_from_mongo import IndexFromMongo


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

        elastic_index_prefix = cast(str, get_app_config("ELASTICSEARCH_INDEX"))
        content_api_index_prefix = cast(str, get_app_config("CONTENTAPI_ELASTICSEARCH_INDEX"))

        if sd_index:
            self.delete_elastic(elastic_index_prefix)
            await self.index_from_mongo(elastic_index_prefix)

        # delete content_api's index if it's not the same as default one
        if capi_index and elastic_index_prefix != content_api_index_prefix:
            self.delete_elastic(content_api_index_prefix)
            await self.index_from_mongo(content_api_index_prefix)

    def delete_elastic(self, index_prefix):
        """Deletes elastic indices with `index_prefix`

        :param str index_prefix: elastix index
        :raise: SystemExit exception if delete elastic index response status is not 200 or 404.
        """

        indices = self._es.indices.get(index=f"{index_prefix}_*")
        for index in indices:
            try:
                print("Deleting index", index)
                self._es.indices.delete(index=index)
            except es_exceptions.NotFoundError:
                pass
            except es_exceptions.RequestError as e:
                if e.status_code not in [200, 404]:
                    raise SystemExit(f"Failed to delete elastic index: {e}")

        # now delete indices for async resources
        get_current_async_app().elastic.drop_indexes(index_prefix)

    async def index_from_mongo(self, index_prefix: str):
        """
        Index elastic search from mongo for all the resources in the given `index_prefix`.
        """
        app = get_current_app()
        await app.data.init_elastic(app)
        resources = app.data.get_elastic_resources()

        for resource in resources:
            # get es prefix per resource
            es_backend = app.data._search_backend(resource)

            # skip those that do not belong to the given index
            resource_index = es_backend._resource_index(resource)
            if resource_index != f"{index_prefix}_{resource}":
                continue

            print(f'Indexing mongo collections into "{index_prefix}" elastic index.')
            IndexFromMongo.copy_resource(resource, IndexFromMongo.default_page_size)

        # let's now index async resources
        self._index_from_mongo_async_resources(index_prefix)

    def _index_from_mongo_async_resources(self, index_prefix: str | None = None):
        """
        Index into elastic search from mongo async resources. If `index_prefix` is provided,
        only the resources that belong to that index prefix will be indexed.
        """
        async_app = get_current_async_app()
        for config in async_app.resources.get_all_configs():
            if config.elastic is None:
                continue

            resource_name = config.name
            if index_prefix:
                resource_elastic_config = async_app.elastic.get_client_async(resource_name).config
                if resource_elastic_config.index != f"{index_prefix}_{resource_name}":
                    continue

            IndexFromMongo.copy_resource(resource_name, IndexFromMongo.default_page_size)


@cli.command("app:flush_elastic_index")
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
