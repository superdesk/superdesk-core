# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2024 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from typing import Union, Annotated, Optional, List, Dict
from typing_extensions import dataclass_transform
from dataclasses import dataclass as python_dataclass, field as dataclass_field
from copy import deepcopy

from pydantic import BaseModel, ConfigDict, Field
from pydantic.dataclasses import dataclass as pydataclass

from .fields import ObjectId


model_config = ConfigDict(
    arbitrary_types_allowed=True,
    validate_assignment=True,  # Revalidate on field assignment
    populate_by_name=True,
)


@dataclass_transform(field_specifiers=(dataclass_field, Field))
def dataclass(*args, **kwargs):
    """Superdesk Dataclass, that enables same config as `ResourceModel` such as assignment validation"""

    return pydataclass(*args, **kwargs, config=model_config)


class ResourceModel(BaseModel):
    """Base ResourceModel class to be used for all registered resources"""

    model_config = model_config

    #: ID of the document
    id: Annotated[Union[str, ObjectId], Field(alias="_id")]


class ResourceModelWithObjectId(ResourceModel):
    """Base ResourceModel class to be used, if the resource uses an ObjectId for it's ID"""

    #: ID of the document
    id: Annotated[ObjectId, Field(alias="_id")]


@python_dataclass
class ResourceModelConfig:
    """A config for a Resource to be registered"""

    #: Name of the resource (must be unique in the system)
    name: str

    #: The ResourceModel class for this resource (used to generate the Elasticsearch mapping)
    data_class: type[ResourceModel]

    #: The config used for MongoDB
    mongo: Optional["MongoResourceConfig"] = None

    #: The config used for Elasticsearch, if `None` then this resource will not be available in Elasticsearch
    elastic: Optional["ElasticResourceConfig"] = None


class Resources:
    """A high level resource class used to manage all resources in the system"""

    _resource_configs: Dict[str, ResourceModelConfig]

    #: A reference back to the parent app, for configuration purposes
    app: "SuperdeskAsyncApp"

    def __init__(self, app: "SuperdeskAsyncApp"):
        self._resource_configs = {}
        self.app = app

    def register(self, config: ResourceModelConfig):
        """Register a new resource in the system

        This will also register the resource with Mongo and optionally Elasticsearch

        :param config: A ResourceModelConfig of the resource to be registered
        :raises KeyError: If the resource has already been registered
        """

        if config.name in self._resource_configs:
            raise KeyError(f"Resource '{config.name}' already registered")

        print(f"Registering {config.name}")
        print(config.data_class)
        for name, field in config.data_class.model_fields.items():
            print(f"name={name}, field={field}")
            # print("\t" + config.data_class[name])

        self._resource_configs[config.name] = config

        self.app.mongo.register_resource_config(
            config.name,
            config.mongo or MongoResourceConfig(),
        )

        if config.elastic is not None:
            self.app.elastic.register_resource_config(
                config.name,
                config.elastic,
            )

    def get_config(self, name: str) -> ResourceModelConfig:
        """Get the config for a registered resource

        :param name: The name of the registered resource
        :return: A copy of the ResourceModelConfig of the registered resource
        :raises KeyError: If the resource is not registered
        """

        return deepcopy(self._resource_configs[name])

    def get_all_configs(self) -> List[ResourceModelConfig]:
        """Get a copy of the configs for all the registered resources in the system"""

        return deepcopy(list(self._resource_configs.values()))


from ..app import SuperdeskAsyncApp  # noqa: E402
from ..mongo import MongoResourceConfig  # noqa: E402
from ..elastic import ElasticResourceConfig  # noqa: E402
