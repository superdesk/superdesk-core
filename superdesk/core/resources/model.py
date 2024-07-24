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
)
from typing_extensions import dataclass_transform, override, Self
from dataclasses import dataclass as python_dataclass, field as dataclass_field
from copy import deepcopy
from inspect import get_annotations
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field
from pydantic.dataclasses import dataclass as pydataclass

from .fields import ObjectId


model_config = ConfigDict(
    arbitrary_types_allowed=True,
    validate_assignment=True,  # Revalidate on field assignment
    populate_by_name=True,
    revalidate_instances="always",
    extra="forbid",
    protected_namespaces=(),
)


@dataclass_transform(field_specifiers=(dataclass_field, Field))
def dataclass(*args, **kwargs):
    """Superdesk Dataclass, that enables same config as `ResourceModel` such as assignment validation"""

    config = deepcopy(model_config)
    config.update(kwargs.pop("config", {}))

    return pydataclass(*args, **kwargs, config=model_config)


class ResourceModel(BaseModel):
    """Base ResourceModel class to be used for all registered resources"""

    model_config = model_config
    model_resource_name: ClassVar[str]  # Automatically set when registered

    @computed_field(alias="_type")  # type: ignore[misc]
    @property
    def type(self) -> str:
        return self.model_resource_name

    #: ID of the document
    id: Annotated[Union[str, ObjectId], Field(alias="_id")]

    #: Datetime the document was created
    created: Annotated[Optional[datetime], Field(alias="_created")] = None

    #: Datetime the document was last updated
    updated: Annotated[Optional[datetime], Field(alias="_updated")] = None

    async def validate_async(self):
        await _run_async_validators_from_model_class(self, self)

    @override
    @classmethod
    def model_validate(
        cls: Type[Self],
        obj: Dict[str, Any],
        *,
        strict: bool | None = None,
        from_attributes: bool | None = None,
        context: dict[str, Any] | None = None,
    ) -> Self:
        """Construct a model instance from the provided dictionary, and validate its values

        :param obj: Dictionary of values used to construct the model instance
        :param strict: Whether to enforce types strictly
        :param from_attributes: Whether to extract data from object attributes
        :param context: Additional context to pass to the validator
        :raises Pydantic.ValidationError: If validation fails
        :rtype: ResourceModel
        :returns: The validated model instance
        """

        item_type = obj.pop("_type", None)
        instance = super().model_validate(
            obj,
            strict=strict,
            from_attributes=from_attributes,
            context=context,
        )
        if item_type is not None:
            obj["_type"] = item_type
        return instance


async def _run_async_validators_from_model_class(
    model_instance: Any, root_item: ResourceModel, field_name_stack: Optional[List[str]] = None
):
    if field_name_stack is None:
        field_name_stack = []

    annotations = get_annotations(model_instance.__class__)

    for field_name, annotation in annotations.items():
        value = getattr(model_instance, field_name)
        metadata = getattr(annotation, "__metadata__", None)

        if metadata is not None:
            for m in metadata:
                if isinstance(m, AsyncValidator):
                    try:
                        await m.func(root_item, value)
                    except ValueError as e:
                        field_full_name = ".".join(field_name_stack + [field_name])
                        raise ValueError(f"Invalid value '{field_full_name}={value}': {e}")

        if isinstance(value, list):
            for val in value:
                await _run_async_validators_from_model_class(val, root_item, field_name_stack + [field_name])
        else:
            await _run_async_validators_from_model_class(value, root_item, field_name_stack + [field_name])


class ResourceModelWithObjectId(ResourceModel):
    """Base ResourceModel class to be used, if the resource uses an ObjectId for it's ID"""

    #: ID of the document
    id: Annotated[ObjectId, Field(alias="_id")]


@python_dataclass
class ResourceConfig:
    """A config for a Resource to be registered"""

    #: Name of the resource (must be unique in the system)
    name: str

    #: The ResourceModel class for this resource (used to generate the Elasticsearch mapping)
    data_class: type[ResourceModel]

    #: The config used for MongoDB
    mongo: Optional["MongoResourceConfig"] = None

    #: The config used for Elasticsearch, if `None` then this resource will not be available in Elasticsearch
    elastic: Optional["ElasticResourceConfig"] = None

    #: Optional ResourceService class, if not provided the system will create a generic one, with no resource type
    service: Optional[Type["AsyncResourceService"]] = None

    #: Optional config to be used for REST endpoints. If not provided, REST will not be available for this resource
    rest_endpoints: Optional["RestEndpointConfig"] = None


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

        self.app.mongo.register_resource_config(
            config.name,
            config.mongo or MongoResourceConfig(),
        )

        if config.elastic is not None:
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
