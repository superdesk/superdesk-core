from bson import ObjectId
from superdesk.types import ProductsResource

NSW_PRODUCT_ID = ObjectId()
ABCDEF_PRODUCT_ID = ObjectId()
XYZ_PRODUCT_ID = ObjectId()


def nsw_product() -> ProductsResource:
    return ProductsResource(
        id=NSW_PRODUCT_ID,
        name="NSW",
        geo_restrictions="NSW",
    )


def abcdef_product() -> ProductsResource:
    return ProductsResource(
        id=ABCDEF_PRODUCT_ID,
        name="abcdef",
        codes="abc,def",
    )


def xyz_product() -> ProductsResource:
    return ProductsResource(
        id=XYZ_PRODUCT_ID,
        name="xyz",
        codes="xyz",
    )


def all_products() -> list[ProductsResource]:
    return [nsw_product(), abcdef_product(), xyz_product()]
