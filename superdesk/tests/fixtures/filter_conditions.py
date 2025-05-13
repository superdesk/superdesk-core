from bson import ObjectId
from superdesk.types import FilterConditionsResource, FilterConditionOperator

FILTER_CONDITION_TEXT_ID = ObjectId()
FILTER_CONDITION_PICTURE_ID = ObjectId()
FILTER_CONDITION_VIDEO_ID = ObjectId()


def filter_condition_text() -> FilterConditionsResource:
    return FilterConditionsResource(
        id=FILTER_CONDITION_TEXT_ID,
        name="All Text",
        field="type",
        operator=FilterConditionOperator.EQUALS,
        value="text",
    )


def filter_condition_picture() -> FilterConditionsResource:
    return FilterConditionsResource(
        id=FILTER_CONDITION_PICTURE_ID,
        name="All Pictures",
        field="type",
        operator=FilterConditionOperator.EQUALS,
        value="picture",
    )


def filter_condition_video() -> FilterConditionsResource:
    return FilterConditionsResource(
        id=FILTER_CONDITION_VIDEO_ID,
        name="All Videos",
        field="type",
        operator=FilterConditionOperator.EQUALS,
        value="video",
    )


def all_filter_conditions() -> list[FilterConditionsResource]:
    return [filter_condition_picture(), filter_condition_video()]
