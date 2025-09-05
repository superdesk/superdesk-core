import elasticsearch

from .common import TestAppContext


def drop_all_elastic_databases(context: TestAppContext) -> None:
    context.async_app.elastic.drop_indexes()
    if context.factory.init_eve_resources:
        context.app.data.elastic.drop_index()


def delete_all_elastic_documents(context: TestAppContext) -> None:
    for resource_config in context.async_app.resources.get_all_configs():
        if not resource_config.elastic:
            continue

        try:
            es_client = context.async_app.elastic.get_client(resource_config.name)
            es_client.elastic.indices.refresh(index=es_client.config.index)
            es_client.elastic.delete_by_query(
                index=es_client.config.index,
                body={"query": {"match_all": {}}},
                refresh=True,
            )
        except elasticsearch.exceptions.NotFoundError:
            print(f"ES Index not found for {resource_config.name}")
            pass


def init_elastic_indexes(context: TestAppContext) -> None:
    context.async_app.elastic.init_all_indexes()

    if context.factory.init_eve_resources:
        # TODO-PR
        pass


async def close_all_elastic_connections(context: TestAppContext) -> None:
    if not getattr(context, "app", None):
        return

    async with context.app.app_context():
        context.app.data.elastic.es.close()
        for es_con in context.app.data.elastic.elastics.values():
            es_con.close()

        await context.app.data.elastic_async.es_async.close()
        for es_async_con in context.app.data.elastic_async.elastics.values():
            await es_async_con.close()
