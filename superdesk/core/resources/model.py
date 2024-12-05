# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2024 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from typing import (
    Union,
    Annotated,
    Optional,
    List,
    Dict,
    Type,
    Any,
    ClassVar,
    cast,
)
from typing_extensions import dataclass_transform, Self
from dataclasses import dataclass as python_dataclass, field as dataclass_field
from copy import deepcopy
from inspect import get_annotations
from datetime import datetime

from pydantic import (
    ConfigDict,
    Field,
    computed_field,
    ValidationError,
    model_serializer,
    SerializerFunctionWrapHandler,
    RootModel,
)
from pydantic_core import InitErrorDetails, PydanticCustomError, from_json
from pydantic.dataclasses import dataclass as pydataclass

from superdesk.core.types import SortListParam, ProjectedFieldArg, BaseModel
from superdesk.core.utils import generate_guid, GUID_NEWSML

from .utils import get_model_aliased_fields
from .fields import ObjectId


default_model_config = ConfigDict(
    arbitrary_types_allowed=True,
    validate_assignment=True,  # Revalidate on field assignment
    populate_by_name=True,
    revalidate_instances="always",
    extra="allow",  # Allow any fields not defined in the ResourceModel/dataclass
    protected_namespaces=(),
)


@dataclass_transform(field_specifiers=(dataclass_field, Field))
def dataclass(*args, **kwargs):
    """Superdesk Dataclass, that enables same config as `ResourceModel` such as assignment validation"""

    config = deepcopy(default_model_config)
    # By default, we allow extra values in dataclasses, but they won't be included in to_dict output.
    config.update(kwargs.pop("config", {}))

    return pydataclass(*args, **kwargs, config=config)


class DataclassBase:
    """Provides type-safe utility methods for Dataclass."""

    @model_serializer(mode="wrap")
    def ser_model(self, nxt: SerializerFunctionWrapHandler):
        """
        Serialize the model, including extra fields not part of the schema.
        """
        aliased_fields = get_model_aliased_fields(self.__class__)
        result = nxt(self)

        # Include extra fields that were not part of the schema for this class
        for key, value in self.__dict__.items():
            if key not in result and key not in aliased_fields:
                # If this key is not already in the result dictionary, and is not an aliased field
                # then add it to the key, as an unknown field
                result[key] = value

        return result

    @classmethod
    def from_dict(cls: type[Self], values: dict[str, Any]) -> Self:
        return cls(**values)

    @classmethod
    def from_json(cls: type[Self], data: str | bytes | bytearray) -> Self:
        values = from_json(data)
        return cls(**values)

    def to_dict(self, **kwargs) -> dict[str, Any]:
        default_params: dict[str, Any] = {"by_alias": True, "exclude_unset": True}
        default_params.update(kwargs)
        return RootModel(self).model_dump(**default_params)

    def to_json(self, **kwargs) -> str:
        default_params: dict[str, Any] = {"by_alias": True, "exclude_unset": True}
        default_params.update(kwargs)
        return RootModel(self).model_dump_json(**default_params)


@dataclass_transform(field_specifiers=(dataclass_field, Field))
class DataclassMeta(type):
    """Metaclass to enhance Dataclass functionality."""

    def __new__(cls: type, name: str, bases: tuple[type, ...], attrs: dict[str, Any]) -> type:
        custom_config = attrs.pop("Config", {})

        # merge with default configuration
        config = deepcopy(default_model_config)
        config.update(custom_config)

        # create the class and apply the Pydantic dataclass decorator
        new_cls = super().__new__(cls, name, bases, attrs)  # type: ignore[misc]
        return pydataclass(new_cls, config=config)


class Dataclass(DataclassBase, metaclass=DataclassMeta):
    """Unified base class for dataclasses with Pydantic features."""

    pass


class ResourceModel(BaseModel):
    """Base ResourceModel class to be used for all registered resources"""

    model_config = default_model_config
    model_resource_name: ClassVar[str]  # Automatically set when registered

    @computed_field(alias="_type")  # type: ignore[misc]
    @property
    def type(self) -> str:
        return self.model_resource_name

    #: ID of the document
    id: Annotated[Union[str, ObjectId], Field(alias="_id", default_factory=lambda: generate_guid(type=GUID_NEWSML))]

    #: Etag of the document
    etag: Annotated[Optional[str], Field(alias="_etag")] = None

    #: Datetime the document was created
    created: Annotated[Optional[datetime], Field(alias="_created")] = None

    #: Datetime the document was last updated
    updated: Annotated[Optional[datetime], Field(alias="_updated")] = None

    async def validate_async(self):
        await _run_async_validators_from_model_class(self, self)

    @classmethod
    def uses_objectid_for_id(cls) -> bool:
        try:
            return cls.model_fields["id"].annotation == ObjectId
        except KeyError:
            return False

    def to_dict(self, **kwargs) -> dict[str, Any]:
        """
        Convert the model instance to a dictionary representation with non-JSON-serializable Python objects.

        :param kwargs: Optional keyword arguments to override the default parameters of model_dump.
        :rtype: dict[str, Any]
        :returns: A dictionary representation of the model instance with field aliases.
                Only fields that are set (non-default) will be included.
        """
        model_dict = super().to_dict(**kwargs)
        if not model_dict.get("_id"):
            # Make sure to include `id`, in case a default one was provided
            # as exclude_unset will not include it when serialising
            model_dict["_id"] = self.id
        return model_dict

    @classmethod
    def from_dict(
        cls,
        values: dict[str, Any],
        context: dict[str, Any] | None = None,
        include_unknown: bool | None = None,
    ) -> Self:
        """Construct a model instance from the provided dictionary, and validate its values

        If ``include_unknown`` is not provided it will default to ``True`` if extra fields are allowed, ``False`` otherwise

        :param values: Dictionary of values used to construct the model instance
        :param context: Additional context to pass to the validator
        :param include_unknown: Whether to include fields not defined in the ResourceModel
        :raises Pydantic.ValidationError: If validation fails
        :rtype: ResourceModel
        :returns: The validated model instance
        """

        if include_unknown is None:
            include_unknown = cls.model_config.get("extra") != "forbid"

        return super().from_dict(values, context, include_unknown)

    @classmethod
    def get_service(cls) -> "AsyncResourceService[Self]":
        """Helper function to get the service for this resource, without needing to import the service directly.

        This should help reduce circular imports when all that is required is to use the base resource service,
        while still providing proper typing.

        Example::

            from bson import ObjectId
            from newsroom.types import UserResourceModel

            async def get_user_email(user_id: ObjectId) -> str | None:
                user = await UserResourceModel.get_service().find_by_id(user_id)
                return user.email if user else None

        :rtype: AsyncResourceService[Self]
        :returns: Async resource service instance for this resource model
        """

        from superdesk.core import get_current_async_app

        app = get_current_async_app()
        return app.resources.get_resource_service(cls.model_resource_name)


async def _run_async_validators_from_model_class(
    model_instance: Any, root_item: ResourceModel, field_name_stack: Optional[List[str]] = None
):
    if field_name_stack is None:
        field_name_stack = []

    model_class = model_instance.__class__

    try:
        annotations = {}
        for base_class in reversed(model_class.__mro__):
            if base_class != ResourceModel and issubclass(base_class, ResourceModel):
                annotations.update(get_annotations(base_class))
    except (TypeError, AttributeError):
        annotations = get_annotations(model_class)

    for field_name, annotation in annotations.items():
        value = getattr(model_instance, field_name)
        metadata = getattr(annotation, "__metadata__", None)

        try:
            if metadata is not None:
                for m in metadata:
                    if isinstance(m, AsyncValidator):
                        await m.func(root_item, value)

            if isinstance(value, list):
                for val in value:
                    await _run_async_validators_from_model_class(val, root_item, field_name_stack + [field_name])
            else:
                await _run_async_validators_from_model_class(value, root_item, field_name_stack + [field_name])
        except PydanticCustomError as error:
            raise ValidationError.from_exception_data(
                model_instance.__class__.__name__,
                line_errors=[
                    InitErrorDetails(
                        type=error,
                        loc=tuple(field_name_stack + [field_name]),
                        input=value,
                        ctx=dict(
                            error=str(error),
                        ),
                    )
                ],
            )
        except ValueError as error:
            raise ValidationError.from_exception_data(
                model_instance.__class__.__name__,
                line_errors=[
                    InitErrorDetails(
                        type="value_error",
                        loc=tuple(field_name_stack + [field_name]),
                        input=value,
                        ctx=dict(
                            error=str(error),
                        ),
                    )
                ],
            )


class ResourceModelWithObjectId(ResourceModel):
    """Base ResourceModel class to be used, if the resource uses an ObjectId for it's ID"""

    #: ID of the document
    id: Annotated[ObjectId, Field(alias="_id", default_factory=ObjectId)]


@dataclass
class ModelWithVersions:
    """Mixin model class to be used to automatically add versions when managed through ``AsyncResourceService``"""

    #: The current version of this document
    current_version: Annotated[Optional[int], Field(alias="_current_version")] = None

    #: The latest version of this document, populated by the ``AsyncResourceService`` service
    latest_version: Annotated[Optional[int], Field(alias="_latest_version")] = None


def model_has_versions(model: ResourceModel | type[ResourceModel]) -> bool:
    """Helper function to determine if the provided resource contains the ``ModelWithVersions`` mixin"""

    return issubclass(type(model), ModelWithVersions)


def get_versioned_model(model: ResourceModel) -> ModelWithVersions | None:
    """Helper function to return an instance of ``ModelWithVersions`` if model has versions, else ``None``"""

    return None if not model_has_versions(model) else cast(ModelWithVersions, model)


@python_dataclass
class ResourceConfig:
    """A config for a Resource to be registered"""

    #: Name of the resource (must be unique in the system)
    name: str

    #: The ResourceModel class for this resource (used to generate the Elasticsearch mapping)
    data_class: type[ResourceModel]

    #: Optional title used in HATEOAS (and docs), will fallback to the class name
    title: str | None = None

    #: The config used for MongoDB
    mongo: Optional["MongoResourceConfig"] = None

    #: The config used for Elasticsearch, if `None` then this resource will not be available in Elasticsearch
    elastic: Optional["ElasticResourceConfig"] = None

    #: Optional ResourceService class, if not provided the system will create a generic one, with no resource type
    service: Optional[Type["AsyncResourceService"]] = None

    #: Optional config to be used for REST endpoints. If not provided, REST will not be available for this resource
    rest_endpoints: Optional["RestEndpointConfig"] = None

    #: Optional config to query and store ObjectIds as strings in MongoDB
    query_objectid_as_string: bool = False

    #: Boolean to indicate if etag concurrency control should be used (defaults to ``True``)
    uses_etag: bool = True

    #: Optional list of resource fields to ignore when generating the etag
    etag_ignore_fields: Optional[list[str]] = None

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


class Resources:
    """A high level resource class used to manage all resources in the system"""

    _resource_configs: Dict[str, ResourceConfig]

    _resource_services: Dict[str, "AsyncResourceService"]

    #: A reference back to the parent app, for configuration purposes
    app: "SuperdeskAsyncApp"

    def __init__(self, app: "SuperdeskAsyncApp"):
        self._resource_configs = {}
        self._resource_services = {}
        self.app = app

    def register(self, config: ResourceConfig):
        """Register a new resource in the system

        This will also register the resource with Mongo and optionally Elasticsearch

        :param config: A ResourceConfig of the resource to be registered
        :raises KeyError: If the resource has already been registered
        """

        if config.name in self._resource_configs:
            raise KeyError(f"Resource '{config.name}' already registered")

        self._resource_configs[config.name] = config

        config.data_class.model_resource_name = config.name
        if not config.datasource_name:
            config.datasource_name = config.name

        mongo_config = config.mongo or MongoResourceConfig()
        if config.versioning:
            mongo_config.versioning = True

        self.app.mongo.register_resource_config(config.name, mongo_config)

        if config.elastic is not None:
            if config.default_sort:
                config.elastic.default_sort = config.default_sort
            self.app.elastic.register_resource_config(
                config.name,
                config.elastic,
            )

        if config.service is None:

            class GenericResourceService(AsyncResourceService):
                pass

            GenericResourceService.resource_name = config.name
            GenericResourceService.config = config
            config.service = GenericResourceService

        config.service.resource_name = config.name
        self._resource_services[config.name] = config.service()

    def get_config(self, name: str) -> ResourceConfig:
        """Get the config for a registered resource

        :param name: The name of the registered resource
        :return: A copy of the ResourceConfig of the registered resource
        :raises KeyError: If the resource is not registered
        """

        return deepcopy(self._resource_configs[name])

    def get_all_configs(self) -> List[ResourceConfig]:
        """Get a copy of the configs for all the registered resources in the system"""

        return deepcopy(list(self._resource_configs.values()))

    def get_resource_service(self, resource_name: str) -> "AsyncResourceService":
        return self._resource_services[resource_name]


from ..app import SuperdeskAsyncApp  # noqa: E402
from .service import AsyncResourceService  # noqa: E402
from ..mongo import MongoResourceConfig  # noqa: E402
from ..elastic import ElasticResourceConfig  # noqa: E402
from .validators import AsyncValidator  # noqa: E402
from .resource_rest_endpoints import RestEndpointConfig  # noqa: E402
