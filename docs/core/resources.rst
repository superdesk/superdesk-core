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

Validation can be added to fields, either by using Pydantic's `Field <https://docs.pydantic.dev/latest/concepts/fields/>`_
class, validators provided by Superdesk, or build your own custom validation. These validations are synchronous,
and are validated when the model instance is constructed.

Example using Pydantic's Field for validation::

    from pydantic import Field
    from superdesk.core.resources import dataclass

    @dataclass
    class Geopoint:
        lat: float = Field(ge=-90, le=90)
        long: float = Field(ge=-180, le=180)


Superdesk provides the following set of validators:

.. autofunction:: superdesk.core.resources.validators.validate_email

.. autofunction:: superdesk.core.resources.validators.validate_minlength

.. autofunction:: superdesk.core.resources.validators.validate_maxlength

Example using Superdesk provided validations::

    from typing import Optional, List, Dict, Set, Annotated
    from superdesk.core.resources import ResourceModel
    from superdesk.core.resources.validators import (
        validate_email,
        validate_minlength,
        validate_maxlength,
    )

    class User(ResourceModel):
        email: Annotated[
            str,
            validate_email(),
            validate_minlength(1),
            validate_maxlength(255),
        ]


Async Validation
----------------

Superdesk also provides async validators. Async validators provide a way to validate data using async code.
Common use cases are unique values or data relationships. These validators are not executed when the model
instance is created, but must be manually run using the ``validate_async`` function.

The following async validators are provided:

.. autofunction:: superdesk.core.resources.validators.validate_data_relation_async

.. autofunction:: superdesk.core.resources.validators.validate_unique_value_async

.. autofunction:: superdesk.core.resources.validators.validate_iunique_value_async

Applying async validators to a field is no different than with regular sync validators.::

    from typing import Optional
    from superdesk.core.resources.validators import (
        validate_data_relation_async,
        validate_iunique_value_async,
    )

    class User(ResourceModel):
        email: Annotated[
            str,
            validate_iunique_value_async("users", "email"),
        ]
        created_by: Annotated[
            Optional[str],
            validate_data_relation_async("users", "_id")
        ] = None

    async def test_user():
        user1 = User(
            id="user_1",
            email="john@doe.org",
            created_by="user_unknown"
        )

        # This next line will raise a ValidationError
        # because no user with ``_id=="user_unknown"`` exists
        await user1.validate_async()


Custom Validator
----------------

Custom validators can be developed and added to any field in a model, just like existing validators.

Example synchronous validator::

    from typing import Annotated, Optional
    import re
    from pydantic import AfterValidator

    from superdesk.core.resources import ResourceModel
    from superdesk.core.resources.validators import validate_maxlength

    MinMaxAcceptedTypes = Union[str, list, int, float, None]

    # Define your custom validation function wrapper here
    def validate_minlength(min_length: int) -> AfterValidator:
        """Validates that the value has a minimum length"""

        def _validate_minlength(value: MinMaxAcceptedTypes) -> MinMaxAcceptedTypes:
            # Validate the actual field value inside the wrapper
            if isinstance(value, (type(""), list)):
                if len(value) < min_length:
                    raise ValueError(f"Invalid minlength: {value}")
            elif isinstance(value, (int, float)):
                if value < min_length:
                    raise ValueError(f"Invalid minlength: {value}")
            return value

        # Return the validation function with
        # Pydantic's ``AfterValidator`` wrapper
        return AfterValidator(_validate_minlength)

    class User(ResourceModel):
        ...
        score: Annotated[
            Optional[int],
            validate_minlength(1),
            validate_maxlength(100),
        ] = None


Example asynchronous validator::

    from superdesk.core.app import get_current_async_app
    from superdesk.core.resources.validators import AsyncValidator

    # Define your custom async validation function wrapper here
    def validate_data_relation_async(
        resource_name: str,
        external_field: str = "_id"
    ) -> AsyncValidator:

        async def validate_resource_exists(
            item_id: Union[str, ObjectId, None]
        ) -> None:
            # Validate the actual field value inside the wrapper
            if item_id is None:
                return

            app = get_current_async_app()
            resource_config = app.resources.get_config(resource_name)
            collection = app.mongo.get_collection_async(
                resource_config.name
            )
            if not await collection.find_one({external_field: item_id}):
                raise ValueError(
                    f"{resource_name} with ID {item_id} does not exist"
                )

        return AsyncValidator(validate_resource_exists)

    class User(ResourceModel):
        ...
        created_by: Annotated[
            Optional[str],
            validate_data_relation_async("users", "_id")
        ] = None


Custom Model Validation
-----------------------

You can add custom validation specific to a model by using Pydantic's `model_validator <https://docs.pydantic.dev/latest/api/functional_validators/#pydantic.functional_validators.model_validator>`_
to decorate a classmethod on your model. For example::

    from typing_extensions import Self

    @dataclass
    class Geopoint:
        lat: float
        long: float

        @model_validator(mode="after")
        @classmethod
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


Field Projection
----------------

By default all fields defined in the ResourceModel will be returned from a query. This behaviour can be changed
by providing a field projection parameter.

Types of Projection:
^^^^^^^^^^^^^^^^^^^^

There are two types of field projection:

* **include:** Include only the supplied fields in the response::

    # From Python code
    p1 = ["slugline", "headline"]
    p2 = {"slugline": 1, "headline": 1}
    p3 = {"slugline": True, "headline": True}

    # From a HTTP GET request
    p4 = '?projection=["slugline", "headline"]'
    p5 = '?projection={"slugline":1, "headline": 1}'
    p6 = '?projection={"slugline":true, "headline": true}'

* **exclude:** Exclude the supplied fields from the response::

    # From Python code
    p7 = {"body_html": 0}
    p8 = {"body_html": False}

    # From a HTTP GET request
    p9 = '?projection={"body_html": 0}'
    p10 = '?projection={"body_html": false}'

The following system fields will **always** be returned, regardless of the field projection requested:

* _id
* _type
* _resource
* _etag

Requesting Projection:
^^^^^^^^^^^^^^^^^^^^^^

Field projection can be requested by using one of the following methods:

1. ResourceModel:
"""""""""""""""""
This is the simplest form of field projection. Any data returned will automatically have fields excluded that
aren't configured on the ResourceModel. This allows to restrict the fields managed by the Resource/Service.

2. ResourceConfig:
""""""""""""""""""
You can provide a default projection by defining the
:attr:`ResourceConfig.projection <model.ResourceConfig.projection>` for the resource.
This will be used if a field projection is not requested by the client.

3. SearchRequest:
"""""""""""""""""
The :attr:`SearchRequest.projection <superdesk.core.types.SearchRequest.projection>` can be used from a client
to request field projection.

4. Service Find Method:
"""""""""""""""""""""""
Directly providing the projection argument to the
:attr:`AsyncResourceService.find <service.AsyncResourceService.find>` service method.

Example Usage:
^^^^^^^^^^^^^^

Using the :class:`ResourceModel <model.ResourceModel>` to automatically provide field projection
so two separate resources can manage data in the same underlying MongoDB Collection (for security reasons)::

    from superdesk.core.resources import (
        ResourceModelWithObjectId,
        ResourceConfig,
        AsyncResourceService,
    )

    # Define a common base ResourceModel that will be
    # used by both resources
    class BaseUserResource(ResourceModelWithObjectId):
        email: str
        is_enabled: bool = False

    # Both resources will use the same underlying
    # MongoDB Collection to store our data
    DATASOURCE_NAME = "users"

    # Define a ResourceModel to be used to manage
    # the User's Profile data
    class UserProfile(BaseUserResource):
        first_name: str
        last_name: str

    class UserProfileDB(AsyncResourceService):
        pass

    user_profile_config = ResourceConfig(
        name="user_profiles",
        datasource_name=DATASOURCE_NAME,
        data_class=UserProfile,
        service=UserProfiles,
    )

    # Define a ResourceModel to be used to manage
    # the User's authentication details
    class UserAuth(BaseUserResource):
        password: str

    class UserAuthDB(AsyncResourceService):
        pass

    user_auth_config = ResourceConfig(
        name="user_auth",
        datasource_name=DATASOURCE_NAME,
        data_class=UserAuth,
        service=UserAuthDB,
    )

    async def test_user_management():
        profile_db = UserProfileDB()
        auth_db = UserAuthDB()

        # Create the new user
        user_id = await profile_db.create([dict(
            email="foo@bar.org",
            first_name="foo",
            last_name="bar",
        )])[0]

        # Assign a password, and enable the User
        await auth_db.update(user_id, dict(
            password="some_hash",
            is_enabled=True,
        ))

        # The following will raise exceptions if used

        # Can't manage password using UserProfileDB resource
        await profile_db.update(user_id, dict(
            password="some_other_password",
        ))

        # Can't get password using UserProfileDB resource
        password = (await profile_db.find_one(user_id)).password

        # Can't set names using the UserAuthDB resource
        await auth_db.update(user_id, dict(
            first_name="Larry",
            last_name="Test",
        ))

        # Can't get names using the UserAuthDB resource
        first_name = (await auth_db.find_one(user_id)).first_name

        # But both point to the same document in MongoDB Collection
        profile = (await profile_db.find_one(user_id))
        auth = (await auth_db.find_one(user_id))
        assert profile.id == auth.id


Another use case is for restricting the amount of data returned, especially if one of the fields
may contain a lot of data::

    class ContentModel(ResourceModel):
        slugline: str
        headline: str
        body_html: str  # Possibly big in size

    class ContentDB(AsyncResourceService):
        pass

    content_config = ResourceConfig(
        name="content",
        data_class=ContentModel,
        service=ContentDB
    )

    async def test_projection():
        content_db = ContentDB()
        id = (await content_db.create([dict(
            slugline="test-content",
            headline="Some Test Content",
            body_html="some really" \
                " really" \
                " really" \
                " long" \
                " text"
        )]))[0]

        content = await content_db.find(
            {},
            projection=dict(body_html=0)
        )
        assert "body_html" not in content



Registering Resources
---------------------
The :meth:`Resources.register <model.Resources.register>` method provides a way to register a resource with the system,
using the :class:`ResourceConfig <model.ResourceConfig>` class to provide the resource config.

This will register the resource with MongoDB and optionally the Elasticsearch system. See
:class:`MongoResourceConfig <superdesk.core.types.MongoResourceConfig>` and
:class:`ElasticResourceConfig <superdesk.core.types.ElasticResourceConfig>` for MongoDB and Elastic config options.

Example module::

    from typing import Optional, List
    from typing_extensions import Annotated

    from superdesk.core.module import Module, SuperdeskAsyncApp
    from superdesk.core.resources import (
        ResourceModel,
        ResourceConfig,
        fields,
        MongoResourceConfig,
        MongoIndexOptions,
        ElasticResourceConfig,
    )

    # Define your user model
    class User(ResourceModel):
        first_name: str
        last_name: str
        name: Optional[fields.TextWithKeyword] = None
        bio: Optional[fields.HTML] = None
        code: Optional[fields.Keyword] = None

    # Define the resource config
    user_model_config = ResourceConfig(
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


You can also use the ``resources`` config from a Module to automatically register resources.::

    module = Module(
        name="tests.users",
        resources=[user_model_config],
    )


API References
--------------

.. autoclass:: superdesk.core.resources.resource_manager.Resources
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

.. autoclass:: superdesk.core.resources.resource_config.ResourceConfig
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
