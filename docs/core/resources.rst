.. core_resources:

Resources
=========

.. module:: superdesk.core.resources


Resource Models
---------------

The :class:`ResourceModel <model.ResourceModel>` class is at the heart of the new resources system.
Under the hood it uses the `Pydantic <https://docs.pydantic.dev/>`_ library.

Defining models will provide the following benefits:

* Static type checking
* Automated API documentation
* Data serialization
* Data validation
* Generating Elasticsearch mapping

An example resource model::

    from typing import Optional, List
    from typing_extensions import Annotated

    from superdesk.core.resources import ResourceModel, fields

    class User(ResourceModel):
        first_name: str
        last_name: str
        name: Optional[fields.TextWithKeyword] = None
        bio: Optional[fields.HTML] = None
        code: Optional[fields.Keyword] = None


Resource Fields
---------------

The following are fields available::

    from typing import Optional, List, Dict, Set, Annotated
    from typing_extensions import Annotated
    from superdesk.core.resources import (
        ResourceModel,
        dataclass,
        fields,
    )

    class ExampleResource(ResourceModel):
        # Python standard data types
        my_string: str
        my_int: int
        my_float: float
        my_bool: bool
        my_bytes: bytes

        # String fields with different Elasticsearch mapping
        my_keyword: fields.Keyword
        my_text_with_keyword: fields.TextWithKeyword
        my_html: fields.HTML

        # 3rd party library fields
        my_id: fields.ObjectId

        # Containers
        my_list: List[str]
        my_dict: Dict[str, int]
        my_set: Set[str]

        # Optional fields
        my_optional_name: Optional[str] = None


All of the above will automatically generate an Elasticsearch mapping for us, except for the `Dict` entry.
Unstructured dictionaries will result in a disabled field in Elasticsearch. If the field is required to be
indexed, then you can use a dataclass to define them. For example::

    # Make sure to import 'dataclass' from Superdesk
    # As it will enable assignment validation for us
    from supedesk.core.resources import dataclass

    @dataclass
    class Subject
        qcode: str
        name: str
        scheme: Optional[str] = None


Then use it in your model like so::

    class ExampleResource(ResourceModel):
        ...
        subjects: Optional[List[Subject]] = None



Validation
----------

Custom validation can be added to your models or dataclasses in 2 different ways.

The first is to use Pydantic's `Field <https://docs.pydantic.dev/latest/concepts/fields/>`_ class
to apply pre-defined validations. For example::

    from pydantic import Field
    from superdesk.core.resources import dataclass

    @dataclass
    class Geopoint:
        lat: float = Field(ge=-90, le=90)
        long: float = Field(ge=-180, le=180)


Or you can use `model_validator <https://docs.pydantic.dev/latest/api/functional_validators/#pydantic.functional_validators.model_validator>`_
decorator if you need to provide custom validation. For example::

    from typing_extensions import Self

    @dataclass
    class Geopoint:
        lat: float
        long: float

        @model_validator(mode="after")
        def post_validate(self) -> Self:
            if self.lat < -90.0 or self.lat > 90.0:
                raise ValueError(
                    f"Latitude has invalid value: {self.lat}"
                )
            elif self.lon < -180.0 or self.lon > 180.0:
                raise ValueError(
                    f"Longitude has invalid value: {self.lat}"
                )

            return self

Fields will be validated on assignment. This means a validation error will be raised at the line in code
where the field was assigned a value. For example::

    def set_geopoint(geopoint: Geopoint, vals: Dict[str, Any]):
        # A validation exception will be raised here
        geopoint.lat = vals["lat"]

    location = Geopoint(lat=30, lon=30)
    set_geopoint(location, dict(lat="abcd", lon="efgh"))


Custom Schema
-------------

The Elasticsearch mapping is generated automatically for us based on the field types. If you need a specific
data type that has a different mapping than the default, you can inherit from the
:class:`BaseCustomField <fields.BaseCustomField>` class. For example::

    from superdesk.core.resources import dataclass, fields

    @dataclass
    class Geopoint(fields.BaseCustomField)
        lat: float = Field(ge=-90, le=90)
        long: float = Field(ge=-180, le=180)

        # Custom Elasticsearch mapping
        elastic_mapping = {"type": "geo_point"}

        # OpenAPI schema properties
        json_schema = {
            "type": "object",
            "required": ["lat", "lon"],
            "properties": {
                "lat": {
                    "type": "number",
                    "title": "Latitude",
                },
                "lon": {
                    "type": "number",
                    "title": "Longitude",
                },
            },
        }


Resource Registration
---------------------
The :meth:`Resources.register <model.Resources.register>` method provides a way to register a resource with the system,
using the :class:`ResourceModelConfig <model.ResourceModelConfig>` class to provide the resource config.



This will register the resource with MongoDB and optionally the Elasticsearch system. See
:class:`MongoResourceConfig <superdesk.core.mongo.MongoResourceConfig>` and
:class:`ElasticResourceConfig <superdesk.core.elastic.common.ElasticResourceConfig>` for MongoDB and Elastic config options.

Example module::

    from typing import Optional, List
    from typing_extensions import Annotated

    from superdesk.core.module import Module, SuperdeskAsyncApp
    from superdesk.core.resources import (
        ResourceModel,
        ResourceModelConfig,
        fields,
    )
    from superdesk.core.mongo import (
        MongoResourceConfig,
        MongoIndexOptions,
    )
    from superdesk.core.elastic.resources import ElasticResourceConfig

    # Define your user model
    class User(ResourceModel):
        first_name: str
        last_name: str
        name: Optional[fields.TextWithKeyword] = None
        bio: Optional[fields.HTML] = None
        code: Optional[fields.Keyword] = None

    # Define the resource config
    user_model_config = ResourceModelConfig(
        name="users",
        data_class=User,
        mongo=[
            MongoIndexOptions(
                name="users_name_1",
                keys=[("first_name", 1)],
            )
        ],
        elastic=ElasticResourceConfig()
    )

    def init(app: SuperdeskAsyncApp):
        # Register the resource with the system
        app.resources.register(user_model_config)

    module = Module(name="tests.users", init=init)


Resources References
--------------------

.. autoclass:: superdesk.core.resources.model.Resources
    :member-order: bysource
    :members:

Resource Model
^^^^^^^^^^^^^^

.. autoclass:: superdesk.core.resources.model.ResourceModel
    :member-order: bysource
    :members: id

.. autoclass:: superdesk.core.resources.model.ResourceModelWithObjectId
    :member-order: bysource
    :members: id

.. autoclass:: superdesk.core.resources.model.ResourceModelConfig
    :member-order: bysource
    :members:

String Fields
^^^^^^^^^^^^^
.. autoclass:: superdesk.core.resources.fields.BaseCustomField
    :member-order: bysource
    :members:

.. autoclass:: superdesk.core.resources.fields.CustomStringField
    :member-order: bysource
    :members:

.. autoclass:: superdesk.core.resources.fields.Keyword

.. autoclass:: superdesk.core.resources.fields.TextWithKeyword

.. autoclass:: superdesk.core.resources.fields.HTML

.. autoclass:: superdesk.core.resources.fields.ObjectId

Specific Fields
^^^^^^^^^^^^^^^
.. autoclass:: superdesk.core.resources.fields.Geopoint


Elastic Mapping Modifiers
^^^^^^^^^^^^^^^^^^^^^^^^^
.. autofunction:: superdesk.core.resources.fields.nested_list
