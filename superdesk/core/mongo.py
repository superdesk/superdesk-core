# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2024 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from typing import Dict, List, Optional, Tuple, Any, TypedDict
from dataclasses import dataclass, asdict
from copy import deepcopy
import logging

from pymongo import MongoClient, uri_parser
from pymongo.database import Database, Collection
from pymongo.errors import OperationFailure, DuplicateKeyError
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection

from superdesk.core.types import SortListParam
from superdesk.resource_fields import VERSION_ID_FIELD, CURRENT_VERSION
from .config import ConfigModel

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
    keys: SortListParam

    #: Ensures that the indexed fields do not store duplicate values
    unique: bool = True

    #: Create index in the background, allowing read and write operations to the database while the index builds
    background: bool = True

    #: If True, the index only references documents with the specified field.
    sparse: bool = True

    #: allows users to specify language-specific rules for string comparison
    collation: Optional[MongoIndexCollation] = None

    #: allows to filter documents for this index
    partialFilterExpression: Optional[Dict[str, Any]] = None


@dataclass
class MongoResourceConfig:
    """Resource config for use with MongoDB, to be included with the ResourceConfig"""

    #: Config prefix to be used
    prefix: str = "MONGO"

    #: Optional list of mongo indexes to be created for this resource
    indexes: Optional[List[MongoIndexOptions]] = None

    #: Optional list of mongo indexes to be created for the versioning resource
    version_indexes: Optional[List[MongoIndexOptions]] = None

    #: Boolean determining if this resource supports versioning
    versioning: bool = False


class MongoClientConfig(ConfigModel):
    host: str = "localhost"
    port: int = 27017
    appname: str = "superdesk"
    dbname: str = "superdesk"
    connect: bool = True
    tz_aware: bool = True
    write_concern: Optional[Dict[str, Any]] = {"w": 1}
    replicaSet: Optional[str] = None
    uri: Optional[str] = None
    document_class: Optional[type] = None
    username: Optional[str] = None
    password: Optional[str] = None
    options: Optional[Dict[str, Any]] = None
    auth_mechanism: Optional[str] = None
    auth_source: Optional[str] = None
    auth_mechanism_properties: Optional[str] = None


def get_mongo_client_config(app_config: Dict[str, Any], prefix: str = "MONGO") -> Tuple[Dict[str, Any], str]:
    config = MongoClientConfig.create_from_dict(app_config, prefix)

    client_kwargs: Dict[str, Any] = {
        "appname": config.appname,
        "connect": config.connect,
        "tz_aware": config.tz_aware,
    }

    if config.options is not None:
        client_kwargs.update(config.options)

    if config.write_concern is not None:
        client_kwargs.update(config.write_concern)

    if config.replicaSet is not None:
        client_kwargs["replicaset"] = config.replicaSet

    uri_parser.validate_options(client_kwargs)

    if config.uri is not None:
        host = config.uri
        # raises an exception if uri is invalid
        mongo_settings = uri_parser.parse_uri(host)

        # extract username and password from uri
        if mongo_settings.get("username"):
            client_kwargs["username"] = mongo_settings["username"]
            client_kwargs["password"] = mongo_settings["password"]

        # extract default database from uri
        dbname = mongo_settings.get("database")
        if not dbname:
            dbname = config.dbname

        # extract auth source from uri
        auth_source = mongo_settings["options"].get("authSource")
        if not auth_source:
            auth_source = dbname
    else:
        dbname = config.dbname
        auth_source = dbname
        host = config.host
        client_kwargs["port"] = config.port

    client_kwargs["host"] = host
    client_kwargs["authSource"] = auth_source

    if config.document_class is not None:
        client_kwargs["document_class"] = config.document_class

    auth_kwargs: Dict[str, Any] = {}
    if config.username is not None:
        username = config.username
        password = config.password
        auth = (username, password)
        if any(auth) and not all(auth):
            raise Exception("Must set both USERNAME and PASSWORD or neither")
        client_kwargs["username"] = username
        client_kwargs["password"] = password
        if any(auth):
            if config.auth_mechanism is not None:
                auth_kwargs["authMechanism"] = config.auth_mechanism
            if config.auth_source is not None:
                auth_kwargs["authSource"] = config.auth_source
            if config.auth_mechanism_properties is not None:
                auth_kwargs["authMechanismProperties"] = config.auth_mechanism_properties

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

    def register_resource_config(self, name: str, config: MongoResourceConfig):
        """Register a Mongo resource config

        :raises KeyError: if a resource with the same name already exists
        """

        if name in self._resource_configs:
            raise KeyError(f"Resource '{name}' already registered")

        self._resource_configs[name] = deepcopy(config)

    def get_resource_config(self, resource_name: str) -> MongoResourceConfig:
        """Gets a resource config from a registered resource

        Returns a deepcopy of the config, so the original cannot be modified

        :raises KeyError: if a resource with the provided ``name`` is not registered
        """

        return deepcopy(self._resource_configs[resource_name])

    def get_all_resource_configs(self) -> Dict[str, MongoResourceConfig]:
        """Get configs from all registered resources

        Returns a deepcopy of all configs, so the originals cannot be modified
        """

        return deepcopy(self._resource_configs)

    def get_collection_name(self, resource_name: str, versioning: bool = False) -> str:
        source_name = self.app.resources.get_config(resource_name).datasource_name or resource_name
        return source_name if not versioning else f"{source_name}_versions"

    def reset_all_async_connections(self):
        for client, _db in self._mongo_clients_async.values():
            client.close()

        self._mongo_clients_async.clear()
        for config in self.app.resources.get_all_configs():
            self.get_client_async(config.name)

    def close_all_clients(self):
        """Closes all clients (sync and async) to the Mongo database(s)"""

        for client, _db in self._mongo_clients.values():
            client.close()

        for client, _db in self._mongo_clients_async.values():
            client.close()

        self._mongo_clients.clear()
        self._mongo_clients_async.clear()

    def stop(self):
        """Disconnects all clients and de-registers all resource configs"""

        self.close_all_clients()
        self._resource_configs.clear()

    # sync access
    def get_client(self, resource_name: str, versioning: bool = False) -> Tuple[MongoClient, Database]:
        """Get a synchronous client and a database connection from a registered resource

        Caches the client connection based on the ``resource_name``, so subsequent calls re-use the same
        connection.

        :param resource_name: The name of the registered resource
        :param versioning: If ``True``, will provide client to the versioned collection
        :raises KeyError: if a resource with the provided ``resource_name`` is not registered
        """

        mongo_config = self.get_resource_config(resource_name)
        if versioning and not mongo_config.versioning:
            raise RuntimeError("Attempting to get version client on a resource where it's disabled")

        if not self._mongo_clients.get(mongo_config.prefix):
            client_config, dbname = get_mongo_client_config(self.app.wsgi.config, mongo_config.prefix)
            client: MongoClient = MongoClient(**client_config)
            db = client.get_database(dbname if not versioning else f"{dbname}_versions")
            self._mongo_clients[mongo_config.prefix] = (client, db)

        return self._mongo_clients[mongo_config.prefix]

    def get_db(self, resource_name: str, versioning: bool = False) -> Database:
        """Get a synchronous database connection from a registered resource

        Caches the database connection based on the ``resource_name``, so subsequent calls re-use the same
        connection.

        :param resource_name: The name of the registered resource
        :param versioning: If ``True``, will provide client to the versioned collection
        :raises KeyError: if a resource with the provided ``resource_name`` is not registered
        """

        return self.get_client(resource_name, versioning)[1]

    def get_collection(self, resource_name, versioning: bool = False) -> Collection:
        """Get a collection connection from a registered resource

        Caches the database connection based on the ``resource_name``, so subsequent calls re-use the same
        connection.

        :param resource_name: The name of the registered resource
        :param versioning: If ``True``, will provide client to the versioned collection
        :raises KeyError: if a resource with the provided ``resource_name`` is not registered
        """

        return self.get_db(resource_name, versioning).get_collection(
            self.get_collection_name(resource_name, versioning)
        )

    def create_resource_indexes(self, resource_name: str, ignore_duplicate_keys=False):
        """Creates indexes for a resource

        If the resource config has ``versioning == True``, then indexes will also be created for the
        versioning collection.

        :param resource_name: The name of the registered resource
        :param ignore_duplicate_keys: If ``True``, will ignore duplicate key errors
        :raises KeyError: if a resource with the provided ``resource_name`` is not registered
        """

        mongo_config = self.get_resource_config(resource_name)
        indexes = mongo_config.indexes or []
        if indexes:
            self.create_collection_indexes(
                self.get_collection(resource_name, versioning=False),
                indexes,
                ignore_duplicate_keys,
            )

        if mongo_config.versioning:
            indexes = (mongo_config.version_indexes or []) + [
                MongoIndexOptions(
                    name="_id_document_current_version_1",
                    keys=[(VERSION_ID_FIELD, 1), (CURRENT_VERSION, 1)],
                    background=True,
                    unique=True,
                ),
            ]

            self.create_collection_indexes(
                self.get_collection(resource_name, versioning=True),
                indexes,
                ignore_duplicate_keys,
            )

    def create_collection_indexes(
        self, collection: Collection, indexes: List[MongoIndexOptions], ignore_duplicate_keys: bool = False
    ):
        for index_details in indexes:
            keys = [(key[0], key[1]) for key in index_details.keys]
            kwargs = {key: val for key, val in asdict(index_details).items() if key != "keys" and val is not None}

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

        for resource_name in self.get_all_resource_configs().keys():
            self.create_resource_indexes(resource_name)

    # Async access
    def get_client_async(
        self, resource_name: str, versioning: bool = False
    ) -> Tuple[AsyncIOMotorClient, AsyncIOMotorDatabase]:
        """Get an asynchronous client and a database connection from a registered resource

        Caches the client connection based on the ``resource_name``, so subsequent calls re-use the same
        connection.

        :raises KeyError: if a resource with the provided ``resource_name`` is not registered
        """

        mongo_config = self.get_resource_config(resource_name)
        if versioning and not mongo_config.versioning:
            raise RuntimeError("Attempting to get version client on a resource where it's disabled")

        if not self._mongo_clients_async.get(mongo_config.prefix):
            client_config, dbname = get_mongo_client_config(self.app.wsgi.config, mongo_config.prefix)
            client = AsyncIOMotorClient(**client_config)
            db = client.get_database(dbname if not versioning else f"{dbname}_versions")
            self._mongo_clients_async[mongo_config.prefix] = (client, db)

        return self._mongo_clients_async[mongo_config.prefix]

    def get_db_async(self, resource_name: str, versioning: bool = False) -> AsyncIOMotorDatabase:
        """Get an asynchronous database connection from a registered resource

        Caches the database connection based on the ``resource_name``, so subsequent calls re-use the same
        connection.

        :raises KeyError: if a resource with the provided ``resource_name`` is not registered
        """

        return self.get_client_async(resource_name, versioning)[1]

    def get_collection_async(self, resource_name: str, versioning: bool = False) -> AsyncIOMotorCollection:
        """Get an asynchronous collection connection from a registered resource

        Caches the database connection based on the ``resource_name``, so subsequent calls re-use the same
        connection.

        :raises KeyError: if a resource with the provided ``resource_name`` is not registered
        """

        return self.get_db_async(resource_name, versioning).get_collection(
            self.get_collection_name(resource_name, versioning)
        )


from .app import SuperdeskAsyncApp  # noqa: E402
