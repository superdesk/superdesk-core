from typing import Annotated
from enum import Enum, unique

from superdesk.core.resources import ResourceModelWithObjectId, Dataclass, fields
from superdesk.core.resources.validators import validate_iunique_value_async, validate_data_relation_async


@unique
class ProductTypes(str, Enum):
    API = "api"
    DIRECT = "direct"
    BOTH = "both"


@unique
class ProductFilterType(str, Enum):
    BLOCKING = "blocking"
    PERMITTING = "permitting"


class ProductContentFilter(Dataclass):
    filter_id: Annotated[fields.ObjectId | None, validate_data_relation_async("content_filters")] = None
    filter_type: ProductFilterType = ProductFilterType.BLOCKING


class ProductsResource(ResourceModelWithObjectId):
    name: Annotated[str, validate_iunique_value_async("products", "name")]
    description: str | None = None
    codes: str | None = None
    content_filter: ProductContentFilter | None = None
    geo_restrictions: str | None = None
    product_type: ProductTypes = ProductTypes.BOTH
    init_version: int | None = None

    @classmethod
    async def get_names(cls, lookup: dict) -> list[str]:
        cursor = await cls.get_service().search(lookup)
        return [product.name async for product in cursor]
