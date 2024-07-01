from typing import Optional, List, Dict
from typing_extensions import Annotated

from pydantic import Field

from superdesk.core.module import Module, SuperdeskAsyncApp
from superdesk.core.mongo import MongoResourceConfig, MongoIndexOptions
from superdesk.core.elastic.resources import ElasticResourceConfig

from superdesk.core.resources import ResourceModel, ResourceModelConfig, fields, dataclass


@dataclass
class Category:
    qcode: str
    name: str
    scheme: Optional[str] = None


@dataclass
class RelatedItems:
    id: Annotated[fields.ObjectId, Field(alias="_id")]
    link_type: fields.Keyword
    slugline: fields.HTML


class MyCustomString(str, fields.CustomStringField):
    elastic_mapping = {"type": "text", "analyzer": "html_field_analyzer"}


class User(ResourceModel):
    first_name: str
    last_name: str
    name: Optional[fields.TextWithKeyword] = None
    bio: Optional[fields.HTML] = None
    code: Optional[fields.Keyword] = None
    categories: Annotated[Optional[List[Category]], fields.nested_list()] = []
    profile_id: Optional[fields.ObjectId] = None
    related_items: Optional[Annotated[List[RelatedItems], fields.nested_list()]] = None
    custom_field: Optional[MyCustomString] = None
    score: Optional[float] = None
    location: Optional[fields.Geopoint] = None
    my_dict: Optional[Dict[str, int]] = None


user_model_config = ResourceModelConfig(
    name="users",
    data_class=User,
    mongo=MongoResourceConfig(
        indexes=[
            MongoIndexOptions(
                name="users_name_1",
                keys=[("first_name", 1)],
            ),
            MongoIndexOptions(
                name="combined_name_1",
                keys=[("first_name", 1), ("last_name", -1)],
                background=False,
                unique=False,
                sparse=False,
                collation={"locale": "en", "strength": 1},
            ),
        ],
    ),
    elastic=ElasticResourceConfig(),
)


def init(app: SuperdeskAsyncApp):
    app.resources.register(user_model_config)


module = Module(name="tests.users", init=init)
