import elasticsearch

from superdesk.core.app import SuperdeskAsyncApp
from superdesk.cache import cache


__all__ = ["_clean_es", "drop_mongo", "clean_dbs"]


async def _clean_es(app):
    async with app.app_context():
        app.data.elastic.drop_index()


async def drop_mongo(app):
    pairs = (
        ("MONGO", "MONGO_DBNAME"),
        ("ARCHIVED", "ARCHIVED_DBNAME"),
        ("LEGAL_ARCHIVE", "LEGAL_ARCHIVE_DBNAME"),
        ("CONTENTAPI_MONGO", "CONTENTAPI_MONGO_DBNAME"),
    )
    async with app.app_context():
        for prefix, name in pairs:
            if not app.config.get(name):
                continue
            dbname = app.config[name]
            dbconn = app.data.mongo.pymongo(prefix=prefix).cx
            dbconn.drop_database(dbname)


async def clean_dbs(app=None, async_app: SuperdeskAsyncApp | None = None, force=False, init_indexes: bool = False):
    if async_app is None:
        if app is None:
            raise RuntimeError("Async app not provided nor found")
        async_app = app.async_app

    if init_indexes:
        if app:
            await _clean_es(app)
            await drop_mongo(app)

        if async_app:
            for resource_name, resource_config in async_app.mongo.get_all_resource_configs().items():
                client, db = async_app.mongo.get_client(resource_name)
                client.drop_database(db)
            async_app.elastic.drop_indexes()

        if app:
            app.init_indexes()
            await app.data.init_elastic(app)
        elif async_app:
            async_app.mongo.create_indexes_for_all_resources()
            async_app.elastic.init_all_indexes()

    else:
        resources_processed: set[str] = set()

        if app:
            es = app.data.elastic
            for resource in es._get_elastic_resources():
                alias = es._resource_index(resource)
                try:
                    alias_info = es.elastic(resource).indices.get_alias(name=alias)
                    for index in alias_info:
                        es.elastic(resource).indices.refresh(index=index)
                        es.elastic(resource).delete_by_query(
                            index=index,
                            body={"query": {"match_all": {}}},
                            refresh=True,
                        )
                except elasticsearch.exceptions.NotFoundError:
                    try:
                        es.elastic(resource).indices.refresh(index=alias)
                        es.elastic(resource).delete_by_query(
                            index=alias,
                            body={"query": {"match_all": {}}},
                            refresh=True,
                        )
                    except elasticsearch.exceptions.NotFoundError:
                        pass

                # TODO-ASYNC: Figure out what's going on here, uncommenting this line causes
                # some resources to not be wiped before running tests
                # resources_processed.add(resource)

            await drop_mongo(app)

        if async_app:
            for resource_config in async_app.resources.get_all_configs():
                if resource_config.name in resources_processed:
                    continue

                mongo_client, mongo_db = async_app.mongo.get_client(resource_config.name)
                mongo_client.drop_database(mongo_db)

                if not resource_config.elastic:
                    continue

                try:
                    es_client = async_app.elastic.get_client(resource_config.name)
                    es_client.elastic.indices.refresh(index=es_client.config.index)
                    es_client.elastic.delete_by_query(
                        index=es_client.config.index,
                        body={"query": {"match_all": {}}},
                        refresh=True,
                    )
                except elasticsearch.exceptions.NotFoundError:
                    print(f"ES Index not found for {resource_config.name}")
                    pass

        if app and getattr(cache, "app", None):
            cache.clean()
