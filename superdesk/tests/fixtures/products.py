from bson import ObjectId
from superdesk.types import ProductsResource, ProductTypes, ProductContentFilter, ProductFilterType

from .content_filters import (
    CONTENT_FILTER_TEXT_ID,
    CONTENT_FILTER_MEDIA_ID,
    CONTENT_FILTER_PICTURES_ID,
    CONTENT_FILTER_VIDEOS_ID,
)

TEXT_PRODUCT_ID = ObjectId()
NSW_PRODUCT_ID = ObjectId()
ABCDEF_PRODUCT_ID = ObjectId()
XYZ_PRODUCT_ID = ObjectId()
PICTURE_PRODUCT_ID = ObjectId()
VIDEO_PRODUCT_ID = ObjectId()
MEDIA_PRODUCT_ID = ObjectId()


def text_product() -> ProductsResource:
    return ProductsResource(
        id=TEXT_PRODUCT_ID,
        name="Text Product",
        product_type=ProductTypes.BOTH,
        content_filter=ProductContentFilter(
            filter_id=CONTENT_FILTER_TEXT_ID,
            filter_type=ProductFilterType.PERMITTING,
        ),
    )


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


def picture_product() -> ProductsResource:
    return ProductsResource(
        id=PICTURE_PRODUCT_ID,
        name="Picture Product",
        product_type=ProductTypes.BOTH,
        content_filter=ProductContentFilter(
            filter_id=CONTENT_FILTER_PICTURES_ID,
            filter_type=ProductFilterType.PERMITTING,
        ),
    )


def video_product() -> ProductsResource:
    return ProductsResource(
        id=VIDEO_PRODUCT_ID,
        name="Video Product",
        product_type=ProductTypes.BOTH,
        content_filter=ProductContentFilter(
            filter_id=CONTENT_FILTER_VIDEOS_ID,
            filter_type=ProductFilterType.PERMITTING,
        ),
    )


def media_product() -> ProductsResource:
    return ProductsResource(
        id=MEDIA_PRODUCT_ID,
        name="Picture & Video Product",
        product_type=ProductTypes.BOTH,
        content_filter=ProductContentFilter(
            filter_id=CONTENT_FILTER_MEDIA_ID,
            filter_type=ProductFilterType.PERMITTING,
        ),
    )


def all_products() -> list[ProductsResource]:
    return [nsw_product(), abcdef_product(), xyz_product()]
