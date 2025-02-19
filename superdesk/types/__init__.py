from typing import Any, Dict, List, TypedDict

from .desks import DesksResourceModel
from .users import UsersResourceModel
from .vocabularies import VocabulariesResourceModel

from .products import ProductsResource, ProductTypes, ProductFilterType
from .subscribers import SubscribersResource, SubscriberDestination, SubscriberSequenceSettings, SubscriberType
from .sequences import SequencesResource
from .content_filters import ContentFilterExpression, ContentFilter, ContentFiltersResource
from .filter_conditions import FilterConditionOperator, FilterConditionFieldParam, FilterConditionsResource
from .publish_queue import PublishQueueState, PublishQueueResource

__all__ = [
    "UsersResourceModel",
    "DesksResourceModel",
    "VocabulariesResourceModel",
    "ProductsResource",
    "ProductTypes",
    "ProductFilterType",
    "SubscribersResource",
    "SubscriberDestination",
    "SubscriberSequenceSettings",
    "SubscriberType",
    "SequencesResource",
    "ContentFilterExpression",
    "ContentFilter",
    "ContentFiltersResource",
    "FilterConditionOperator",
    "FilterConditionFieldParam",
    "FilterConditionsResource",
    "PublishQueueState",
    "PublishQueueResource",
]


class WebsocketMessageFilterConditions(TypedDict, total=False):
    include: Dict[str, List[str]]
    exclude: Dict[str, List[str]]


class WebsocketMessageData(TypedDict, total=False):
    event: str
    filters: WebsocketMessageFilterConditions
    extra: Dict[str, Any]
    _created: str  # isoformat
    _process: int


class ItemAuthor(TypedDict):
    uri: str
    parent: str
    name: str
    role: str
    jobtitle: str
    sub_label: str


class Item(TypedDict, total=False):
    headline: str
    slugline: str
    authors: List[ItemAuthor]
    extra: Dict[str, Any]


class UserMandatory(TypedDict):
    email: str
    username: str


class User(UserMandatory, total=False):
    user_preferences: Dict[str, Any]
    needs_activation: bool
    is_enabled: bool
    is_active: bool
