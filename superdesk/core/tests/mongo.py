from os import environ
from pymongo import MongoClient
from pymongo.database import Database

from .common import TestAppContext


def get_mongo_uri(key: str, dbname: str) -> str:
    """Read mongo uri from env variable and replace dbname.

    :param key: env variable name
    :param dbname: mongo db name to use
    """
    env_uri = environ.get(key, "mongodb://localhost/test")
    env_host = env_uri.rsplit("/", 1)[0]
    return "/".join([env_host, dbname])


def get_async_mongo_resources(context: TestAppContext) -> dict[str, tuple[MongoClient, Database]]:
    mongo_prefixes: dict[str, tuple[MongoClient, Database]] = {}
    for name, config in context.async_app.mongo.get_all_resource_configs().items():
        client, db = context.async_app.mongo.get_client(name)
        key = f"{config.prefix}.{db.name}"
        if key not in mongo_prefixes:
            mongo_prefixes[key] = client, db

    return mongo_prefixes


def drop_all_mongo_databases(context: TestAppContext) -> None:
    for client, db in get_async_mongo_resources(context).values():
        client.drop_database(db)

    if context.factory.init_eve_resources:
        drop_eve_mongo_databases(context)


def drop_eve_mongo_databases(context: TestAppContext) -> None:
    pairs = (
        ("MONGO", "MONGO_DBNAME"),
        ("ARCHIVED", "ARCHIVED_DBNAME"),
        ("LEGAL_ARCHIVE", "LEGAL_ARCHIVE_DBNAME"),
        ("CONTENTAPI_MONGO", "CONTENTAPI_MONGO_DBNAME"),
    )
    for prefix, name in pairs:
        if not context.app.config.get(name):
            continue
        dbname = context.app.config[name]
        dbconn = context.app.data.mongo.pymongo(prefix=prefix).cx
        dbconn.drop_database(dbname)


def delete_all_mongo_documents(context: TestAppContext) -> None:
    # Delete all documents, from all collections from all databases configured in this app
    for client, db in get_async_mongo_resources(context).values():
        for collection_name in [c["name"] for c in db.list_collections()]:
            db.get_collection(collection_name).delete_many({})


def init_mongo_indexes(context: TestAppContext) -> None:
    context.async_app.mongo.create_indexes_for_all_resources()

    if context.factory.init_eve_resources:
        # TODO-PR
        pass


def close_all_mongo_connections(context: TestAppContext) -> None:
    """
    Note: Should only be called when constructing a new app instance
    """
    if not getattr(context, "app", None):
        return

    for mongo_con in context.app.data.mongo.driver.values():
        mongo_con.cx.close()

    for mongo_con in context.app.data.mongo_async.driver.values():
        mongo_con.cx.close()

    # TODO-PR: Close all async app db connections

    context.app.extensions["pymongo"] = {}
    context.app.extensions["pymongo_async"] = {}
