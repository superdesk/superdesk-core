from bson import ObjectId
from superdesk.types import ContentFiltersResource, ContentFilter, ContentFilterExpression

from .filter_conditions import FILTER_CONDITION_TEXT_ID, FILTER_CONDITION_PICTURE_ID, FILTER_CONDITION_VIDEO_ID

CONTENT_FILTER_TEXT_ID = ObjectId()
CONTENT_FILTER_PICTURES_ID = ObjectId()
CONTENT_FILTER_VIDEOS_ID = ObjectId()
CONTENT_FILTER_MEDIA_ID = ObjectId()


def content_filter_text() -> ContentFiltersResource:
    return ContentFiltersResource(
        id=CONTENT_FILTER_TEXT_ID,
        name="Text Content Filter",
        content_filter=[ContentFilter(expression=ContentFilterExpression(fc=[FILTER_CONDITION_TEXT_ID]))],
    )


def content_filter_pictures() -> ContentFiltersResource:
    return ContentFiltersResource(
        id=CONTENT_FILTER_PICTURES_ID,
        name="Picture Content Filter",
        content_filter=[ContentFilter(expression=ContentFilterExpression(fc=[FILTER_CONDITION_PICTURE_ID]))],
    )


def content_filter_videos() -> ContentFiltersResource:
    return ContentFiltersResource(
        id=CONTENT_FILTER_VIDEOS_ID,
        name="Video Content Filter",
        content_filter=[ContentFilter(expression=ContentFilterExpression(fc=[FILTER_CONDITION_VIDEO_ID]))],
    )


def content_filter_media() -> ContentFiltersResource:
    return ContentFiltersResource(
        id=CONTENT_FILTER_MEDIA_ID,
        name="Picture & Video Content Filter",
        content_filter=[
            ContentFilter(expression=ContentFilterExpression(fc=[FILTER_CONDITION_PICTURE_ID])),
            ContentFilter(expression=ContentFilterExpression(fc=[FILTER_CONDITION_VIDEO_ID])),
        ],
    )


def all_content_filters() -> list[ContentFiltersResource]:
    return [content_filter_pictures(), content_filter_videos(), content_filter_media()]
