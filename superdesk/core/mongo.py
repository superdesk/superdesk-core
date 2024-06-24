# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2024 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from typing import Dict, List, Optional, Literal, Tuple, Any, TypedDict
from dataclasses import dataclass, asdict
from copy import deepcopy
import logging

from pymongo import MongoClient, uri_parser
from pymongo.database import Database
from pymongo.errors import OperationFailure, DuplicateKeyError
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


class MongoIndexCollation(TypedDict):
    """TypedDict class for ``collation`` config

    See https://www.mongodb.com/docs/manual/core/index-case-insensitive
    """

    #: Specifies language rules
    locale: str

    #: Determines comparison rules. A strength value of 1 or 2 indicates case-insensitive collation
    strength: int


@dataclass
class MongoIndexOptions:
    """Dataclass for easy construction of Mongo Index options

    See https://mongodb.com/docs/manual/reference/method/db.collection.createIndex
    """

    #: Name of the MongoDB Index
    name: str

    #: List of keys to be used for the MongoDB Index
    keys: List[Tuple[str, Literal[1, -1]]]

    #: Ensures that the indexed fields do not store duplicate values
    unique: bool = True

    #: Create index in the background, allowing read and write operations to the database while the index builds
    background: bool = True

    #: If True, the index only references documents with the specified field.
    sparse: bool = True

    #: allows users to specify language-specific rules for string comparison
    collation: Optional[Dict[str, Any]] = None


@dataclass
class MongoResourceConfig:
    #: Name of the Resource (also used for the MongoDB Collection name)
    name: str

    #: Config suffix to be used
    prefix: str = "MONGO"

    #: Optional list of mongo indexes to be created for this resource
    indexes: Optional[List[MongoIndexOptions]] = None

    #: Boolean determining if this resource supports versioning
    versioning: bool = False


def _get_mongo_client_config(app_config: Dict[str, Any], prefix: str = "MONGO") -> Tuple[Dict[str, Any], str]:
    def key(suffice: str) -> str:
        return f"{prefix}_{suffice}"

    def config_to_kwargs(mapping):
        """
        Convert config options to kwargs according to provided mapping
        information.
        """
        kwargs = {}
        for option, arg in mapping.items():
            if key(option) in app_config:
                kwargs[arg] = app_config[key(option)]
        return kwargs

    # Copied from flask_pymongo, so we're not relying on Flask but instead the WSGIApp protocol
    config = {
        key("HOST"): app_config.get(key("HOST"), "localhost"),
        key("PORT"): app_config.get(key("PORT"), 27017),
        key("DBNAME"): app_config.get(key("DBNAME"), "superdesk"),
        key("WRITE_CONCERN"): app_config.get(key("WRITE_CONCERN"), {"w": 1}),
    }

    client_kwargs = {
        "appname": "superdesk",
        "connect": True,  # TODO: Connects straight away, do we change this to False (to connect on first operation)
        "tz_aware": True,
    }
    if key("OPTIONS") in app_config:
        client_kwargs.update(app_config[key("OPTIONS")])

    if key("WRITE_CONCERN") in app_config:
        # w, wtimeout, j and fsync
        client_kwargs.update(app_config[key("WRITE_CONCERN")])

    if key("REPLICA_SET") in app_config:
        client_kwargs["replicaset"] = app_config[key("REPLICA_SET")]

    uri_parser.validate_options(client_kwargs)

    if key("URI") in app_config:
        host = app_config[key("URI")]
        # raises an exception if uri is invalid
        mongo_settings = uri_parser.parse_uri(host)

        # extract username and password from uri
        if mongo_settings.get("username"):
            client_kwargs["username"] = mongo_settings["username"]
            client_kwargs["password"] = mongo_settings["password"]

        # extract default database from uri
        dbname = mongo_settings.get("database")
        if not dbname:
            dbname = config[key("DBNAME")]

        # extract auth source from uri
        auth_source = mongo_settings["options"].get("authSource")
        if not auth_source:
            auth_source = dbname
    else:
        dbname = config[key("DBNAME")]
        auth_source = dbname
        host = config[key("HOST")]
        client_kwargs["port"] = config[key("PORT")]

    client_kwargs["host"] = host
    client_kwargs["authSource"] = auth_source

    if key("DOCUMENT_CLASS") in app_config:
        client_kwargs["document_class"] = app_config[key("DOCUMENT_CLASS")]

    auth_kwargs = {}
    if key("USERNAME") in app_config:
        app_config.setdefault(key("PASSWORD"), None)
        username = app_config[key("USERNAME")]
        password = app_config[key("PASSWORD")]
        auth = (username, password)
        if any(auth) and not all(auth):
            raise Exception("Must set both USERNAME and PASSWORD or neither")
        client_kwargs["username"] = username
        client_kwargs["password"] = password
        if any(auth):
            auth_mapping = {
                "AUTH_MECHANISM": "authMechanism",
                "AUTH_SOURCE": "authSource",
                "AUTH_MECHANISM_PROPERTIES": "authMechanismProperties",
            }
            auth_kwargs = config_to_kwargs(auth_mapping)

    return {**client_kwargs, **auth_kwargs}, dbname


class MongoResources:
    _resource_configs: Dict[str, MongoResourceConfig]
    _mongo_clients: Dict[str, Tuple[MongoClient, Database]]
    _mongo_clients_async: Dict[str, Tuple[AsyncIOMotorClient, AsyncIOMotorDatabase]]

    #: A reference back to the parent app, for configuration purposes
    app: "SuperdeskAsyncApp"

    def __init__(self, app: "SuperdeskAsyncApp"):
        self._resource_configs = {}
        self._mongo_clients = {}
        self._mongo_clients_async = {}
        self.app = app

    def register_resource_config(self, config: MongoResourceConfig):
        """Register a Mongo resource config

        :raises KeyError: if a resource with the same name already exists
        """

        if config.name in self._resource_configs:
            raise KeyError(f"Resource '{config.name}' already registered")

        self._resource_configs[config.name] = deepcopy(config)

    def get_resource_config(self, resource_name: str) -> MongoResourceConfig:
        """Gets a resource config from a registered resource

        Returns a deepcopy of the config, so the original cannot be modified

        :raises KeyError: if a resource with the provided ``name`` is not registered
        """

        return deepcopy(self._resource_configs[resource_name])

    def get_all_resource_configs(self) -> List[MongoResourceConfig]:
        """Get configs from all registered resources

        Returns a deepcopy of all configs, so the originals cannot be modified
        """

        return deepcopy(list(self._resource_configs.values()))

    def close_all_clients(self):
        """Closes all clients (sync and async) to the Mongo database(s)"""

        for resource_config in self.get_all_resource_configs():
            client, _db = self.get_client(resource_config.name)
            client.close()

            client, _db = self.get_client_async(resource_config.name)
            client.close()

        self._mongo_clients.clear()
        self._mongo_clients_async.clear()

    def stop(self):
        """Disconnects all clients and de-registers all resource configs"""

        self.close_all_clients()
        self._resource_configs.clear()

    # sync access
    def get_client(self, resource_name: str) -> Tuple[MongoClient, Database]:
        """Get a synchronous client and a database connection from a registered resource

        Caches the client connection based on the ``resource_name``, so subsequent calls re-use the same
        connection.

        :raises KeyError: if a resource with the provided ``resource_name`` is not registered
        """

        resource_config = self.get_resource_config(resource_name)

        if not self._mongo_clients.get(resource_config.prefix):
            client_config, dbname = _get_mongo_client_config(self.app.wsgi.config, resource_config.prefix)
            client: MongoClient = MongoClient(**client_config)
            db = client.get_database(dbname)
            self._mongo_clients[resource_config.prefix] = (client, db)

        return self._mongo_clients[resource_config.prefix]

    def get_db(self, resource_name: str) -> Database:
        """Get a synchronous database connection from a registered resource

        Caches the database connection based on the ``resource_name``, so subsequent calls re-use the same
        connection.

        :raises KeyError: if a resource with the provided ``resource_name`` is not registered
        """

        return self.get_client(resource_name)[1]

    def create_resource_indexes(self, resource_name: str, ignore_duplicate_keys=False):
        """Creates indexes for a resource

        If the resource config has ``versioning == True``, then a second index with suffix ``_versions``
        will be created.

        :raises KeyError: if a resource with the provided ``resource_name`` is not registered
        """

        resource_config = self.get_resource_config(resource_name)
        db = self.get_client(resource_config.name)[1]
        collection_names = (
            [resource_config.name]
            if not resource_config.versioning
            else [resource_config.name, f"{resource_config.name}_versions"]
        )

        for collection_name in collection_names:
            collection = db.get_collection(collection_name)
            if resource_config.indexes is None:
                continue
            for index_details in resource_config.indexes:
                keys = [
                    # (key.name, key.direction) if key.direction is not None else key.name
                    (key[0], key[1])
                    for key in index_details.keys
                ]
                kwargs = {key: val for key, val in asdict(index_details).items() if key != "keys"}

                try:
                    collection.create_index(keys, **kwargs)
                except DuplicateKeyError as err:
                    # Duplicate key for unique indexes are generally caused by invalid documents in the collection
                    # such as multiple documents not having a value for the attribute used for the index
                    # Log the error so it can be diagnosed and fixed
                    logger.exception(err)

                    if not ignore_duplicate_keys:
                        raise
                except OperationFailure as e:
                    if e.code in (85, 86):
                        # raised when the definition of the index has been changed.
                        # (https://github.com/mongodb/mongo/blob/master/src/mongo/base/error_codes.err#L87)

                        # by default, drop the old index with old configuration and
                        # create the index again with the new configuration.
                        collection.drop_index(index_details.name)
                        collection.create_index(keys, **kwargs)
                    else:
                        raise

    def create_indexes_for_all_resources(self):
        """Creates indexes for all registered resources"""

        for resource_config in self.get_all_resource_configs():
            self.create_resource_indexes(resource_config.name)

    # Async access
    def get_client_async(self, resource_name: str) -> Tuple[AsyncIOMotorClient, AsyncIOMotorDatabase]:
        """Get an asynchronous client and a database connection from a registered resource

        Caches the client connection based on the ``resource_name``, so subsequent calls re-use the same
        connection.

        :raises KeyError: if a resource with the provided ``resource_name`` is not registered
        """

        resource_config = self.get_resource_config(resource_name)

        if not self._mongo_clients_async.get(resource_config.prefix):
            client_config, dbname = _get_mongo_client_config(self.app.wsgi.config, resource_config.prefix)
            client = AsyncIOMotorClient(**client_config)
            db = client.get_database(dbname)
            self._mongo_clients_async[resource_config.prefix] = (client, db)

        return self._mongo_clients_async[resource_config.prefix]

    def get_db_async(self, resource_name: str) -> AsyncIOMotorDatabase:
        """Get an asynchronous database connection from a registered resource

        Caches the database connection based on the ``resource_name``, so subsequent calls re-use the same
        connection.

        :raises KeyError: if a resource with the provided ``resource_name`` is not registered
        """

        return self.get_client_async(resource_name)[1]


from .app import SuperdeskAsyncApp  # noqa: E402
