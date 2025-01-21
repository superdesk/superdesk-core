from typing import Union
from dataclasses import dataclass

from superdesk.core.types import SortListParam, ProjectedFieldArg, MongoResourceConfig, ElasticResourceConfig


@dataclass
class ResourceConfig:
    """A config for a Resource to be registered"""

    #: Name of the resource (must be unique in the system)
    name: str

    #: The ResourceModel class for this resource (used to generate the Elasticsearch mapping)
    data_class: type["ResourceModel"]

    #: Optional title used in HATEOAS (and docs), will fallback to the class name
    title: str | None = None

    #: The config used for MongoDB
    mongo: MongoResourceConfig | None = None

    #: The config used for Elasticsearch, if `None` then this resource will not be available in Elasticsearch
    elastic: ElasticResourceConfig | None = None

    #: Optional ResourceService class, if not provided the system will create a generic one, with no resource type
    service: type["AsyncResourceService"] | None = None

    #: Optional config to be used for REST endpoints. If not provided, REST will not be available for this resource
    rest_endpoints: Union["RestEndpointConfig", None] = None

    #: Optional config to query and store ObjectIds as strings in MongoDB
    query_objectid_as_string: bool = False

    #: Boolean to indicate if etag concurrency control should be used (defaults to ``True``)
    uses_etag: bool = True

    #: Optional list of resource fields to ignore when generating the etag
    etag_ignore_fields: list[str] | None = None

    #: Boolean to indicate if this resource provides a version resource as well
    versioning: bool = False

    #: Optional list of fields not to store in the versioning resource
    ignore_fields_in_versions: list[str] | None = None

    #: Optional sorting for this resource
    default_sort: SortListParam | None = None

    #: Optionally override the name used for the MongoDB/Elastic sources
    datasource_name: str | None = None

    #: Optional projection to be used to include/exclude fields
    projection: ProjectedFieldArg | None = None


from .resource_rest_endpoints import RestEndpointConfig  # noqa: E402
from .model import ResourceModel  # noqa: E402
from .service import AsyncResourceService  # noqa: E402
