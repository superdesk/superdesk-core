from superdesk.cache import cache

from .common import TestAppContext

from .mongo import close_all_mongo_connections, delete_all_mongo_documents, drop_all_mongo_databases, init_mongo_indexes
from .elastic import (
    close_all_elastic_connections,
    delete_all_elastic_documents,
    drop_all_elastic_databases,
    init_elastic_indexes,
)


async def close_all_db_connections(context: TestAppContext) -> None:
    if not getattr(context, "app", None):
        return

    async with context.app.app_context():
        close_all_mongo_connections(context)
        await close_all_elastic_connections(context)


def drop_all_db_databases(context: TestAppContext) -> None:
    drop_all_mongo_databases(context)
    drop_all_elastic_databases(context)


def delete_all_db_documents(context: TestAppContext) -> None:
    delete_all_mongo_documents(context)
    delete_all_elastic_documents(context)
    drop_cache(context)


def init_db_indexes(context: TestAppContext) -> None:
    init_mongo_indexes(context)
    init_elastic_indexes(context)


async def prepare_resources(context: TestAppContext, init_indexes: bool) -> None:
    init_eve = context.factory.init_eve_resources

    if not init_indexes:
        delete_all_db_documents(context)
        return

    # First, delete all the current databases:
    drop_all_db_databases(context)

    # Next we'll reconfigure the databases
    init_db_indexes(context)


def drop_cache(context: TestAppContext) -> None:
    if getattr(context.app.cache, "app", None):
        cache.clean()
