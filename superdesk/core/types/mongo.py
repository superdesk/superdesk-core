from typing import Dict, List, Optional, Any, TypedDict
from dataclasses import dataclass

from .search import SortListParam
from ..config import ConfigModel


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
