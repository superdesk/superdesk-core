from typing import cast
import logging
from copy import copy
import re

from quart_babel import gettext

from superdesk.core import get_config
from superdesk.types import (
    FilterConditionFieldParam,
    FilterConditionOperator,
    VocabulariesResourceModel,
    DesksResourceModel,
    FilterConditionsResource,
)

from superdesk import get_resource_service

from superdesk.publish_async.signals import on_get_available_filter_params
from .items import get_subjectcodeitems


logger = logging.getLogger(__name__)


async def check_similar_filter_conditions(filter_condition: dict) -> list[FilterConditionsResource]:
    """Checks for similar items

    Checks if the given filter condition already exists (for text fields like headline) or
    if there's any other filter condition that contains the given filter
    condition (for controlled vocabulary fields like urgency).
    For example: if filter_condition ['urgency' in 3,4] exists and if
    filter condition ['urgency' in 3] is searched we'll have a match

    :param filter_condition: Filter conditions to be tested
    :return: Returns the list of matching filter conditions
    """
    service = FilterConditionsResource.get_service()
    parameters = await get_available_filter_params()
    parameter = [p for p in parameters if p.field == filter_condition["field"]]
    if "in" in parameter[0].operators or "nin" in parameter[0].operators:
        # this is a controlled vocabulary field so find the overlapping values
        existing_docs = await (
            await service.search(
                {
                    "field": filter_condition["field"],
                    "operator": filter_condition["operator"],
                    "value": {"$regex": re.compile(".*{}.*".format(filter_condition["value"]), re.IGNORECASE)},
                }
            )
        ).to_list()
        parameter[0].operators.remove(filter_condition["operator"])
        existing_docs.extend(
            await (
                await service.search(
                    {
                        "field": filter_condition["field"],
                        "operator": parameter[0].operators[0],
                        "value": {"$not": re.compile(".*{}.*".format(filter_condition["value"]), re.IGNORECASE)},
                    }
                )
            ).to_list()
        )
    else:
        # find the exact matches
        existing_docs = await (
            await service.search(
                {
                    "field": filter_condition["field"],
                    "operator": filter_condition["operator"],
                    "value": {"$regex": re.compile("{}".format(filter_condition["value"]), re.IGNORECASE)},
                }
            )
        ).to_list()
    return existing_docs


async def get_available_filter_params() -> list[FilterConditionFieldParam]:
    values = await _get_field_values()
    fields: list[FilterConditionFieldParam] = [
        FilterConditionFieldParam(
            field="anpa_category",
            label=gettext("ANPA Category"),
            operators=[FilterConditionOperator.IN, FilterConditionOperator.NOT_IN],
            values=values.get("anpa_category", []),
            value_field="qcode",
        ),
        FilterConditionFieldParam(
            field="urgency",
            label=gettext("Urgency"),
            operators=[
                FilterConditionOperator.IN,
                FilterConditionOperator.NOT_IN,
                FilterConditionOperator.EQUALS,
                FilterConditionOperator.NOT_EQUALS,
                FilterConditionOperator.LESS_THAN,
                FilterConditionOperator.LESS_THAN_OR_EQUAL,
                FilterConditionOperator.GREATER_THAN,
                FilterConditionOperator.GREATER_THAN_OR_EQUAL,
            ],
            values=values.get("urgency", []),
            value_field="qcode",
        ),
        FilterConditionFieldParam(
            field="genre",
            label=gettext("Genre"),
            operators=[FilterConditionOperator.IN, FilterConditionOperator.NOT_IN],
            values=values.get("genre", []),
            value_field="qcode",
        ),
        FilterConditionFieldParam(
            field="subject",
            label=gettext("Subject"),
            operators=[FilterConditionOperator.IN, FilterConditionOperator.NOT_IN],
            values=values.get("subject", []),
            value_field="qcode",
        ),
        FilterConditionFieldParam(
            field="priority",
            label=gettext("Priority"),
            operators=[
                FilterConditionOperator.IN,
                FilterConditionOperator.NOT_IN,
                FilterConditionOperator.EQUALS,
                FilterConditionOperator.NOT_EQUALS,
                FilterConditionOperator.LESS_THAN,
                FilterConditionOperator.LESS_THAN_OR_EQUAL,
                FilterConditionOperator.GREATER_THAN,
                FilterConditionOperator.GREATER_THAN_OR_EQUAL,
            ],
            values=values.get("priority", []),
            value_field="qcode",
        ),
        FilterConditionFieldParam(
            field="keywords",
            label=gettext("Keywords"),
            operators=[FilterConditionOperator.IN, FilterConditionOperator.NOT_IN],
        ),
        FilterConditionFieldParam(
            field="slugline",
            label=gettext("Slugline"),
            operators=[
                FilterConditionOperator.IN,
                FilterConditionOperator.NOT_IN,
                FilterConditionOperator.EQUALS,
                FilterConditionOperator.NOT_EQUALS,
                FilterConditionOperator.LIKE,
                FilterConditionOperator.NOT_LIKE,
                FilterConditionOperator.STARTS_WITH,
                FilterConditionOperator.ENDS_WITH,
            ],
        ),
        FilterConditionFieldParam(
            field="type",
            label=gettext("Type"),
            operators=[
                FilterConditionOperator.IN,
                FilterConditionOperator.NOT_IN,
                FilterConditionOperator.EQUALS,
                FilterConditionOperator.NOT_EQUALS,
            ],
            values=values.get("type", []),
            value_field="qcode",
        ),
        FilterConditionFieldParam(
            field="source",
            label=gettext("Source"),
            operators=[
                FilterConditionOperator.IN,
                FilterConditionOperator.NOT_IN,
                FilterConditionOperator.EQUALS,
                FilterConditionOperator.NOT_EQUALS,
                FilterConditionOperator.LIKE,
                FilterConditionOperator.NOT_LIKE,
                FilterConditionOperator.STARTS_WITH,
                FilterConditionOperator.ENDS_WITH,
            ],
        ),
        FilterConditionFieldParam(
            field="headline",
            label=gettext("Headline"),
            operators=[
                FilterConditionOperator.IN,
                FilterConditionOperator.NOT_IN,
                FilterConditionOperator.EQUALS,
                FilterConditionOperator.NOT_EQUALS,
                FilterConditionOperator.LIKE,
                FilterConditionOperator.NOT_LIKE,
                FilterConditionOperator.STARTS_WITH,
                FilterConditionOperator.ENDS_WITH,
            ],
        ),
        FilterConditionFieldParam(
            field="ednote",
            label=gettext("Ednote"),
            operators=[
                FilterConditionOperator.IN,
                FilterConditionOperator.NOT_IN,
                FilterConditionOperator.EQUALS,
                FilterConditionOperator.NOT_EQUALS,
                FilterConditionOperator.LIKE,
                FilterConditionOperator.NOT_LIKE,
                FilterConditionOperator.STARTS_WITH,
                FilterConditionOperator.ENDS_WITH,
            ],
        ),
        FilterConditionFieldParam(
            field="body_html",
            label=gettext("Body HTML"),
            operators=[
                FilterConditionOperator.IN,
                FilterConditionOperator.NOT_IN,
                FilterConditionOperator.LIKE,
                FilterConditionOperator.NOT_LIKE,
                FilterConditionOperator.STARTS_WITH,
                FilterConditionOperator.ENDS_WITH,
            ],
        ),
        FilterConditionFieldParam(
            field="desk",
            label=gettext("Desk"),
            operators=[
                FilterConditionOperator.IN,
                FilterConditionOperator.NOT_IN,
                FilterConditionOperator.EQUALS,
                FilterConditionOperator.NOT_EQUALS,
            ],
            values=values["desk"],
            value_field="_id",
        ),
        FilterConditionFieldParam(
            field="stage",
            label=gettext("Stage"),
            operators=[
                FilterConditionOperator.IN,
                FilterConditionOperator.NOT_IN,
                FilterConditionOperator.EQUALS,
                FilterConditionOperator.NOT_EQUALS,
            ],
            values=values["stage"],
            value_field="_id",
        ),
        FilterConditionFieldParam(
            field="sms",
            label=gettext("SMS"),
            operators=[
                FilterConditionOperator.IN,
                FilterConditionOperator.NOT_IN,
                FilterConditionOperator.EQUALS,
                FilterConditionOperator.NOT_EQUALS,
            ],
            values=values["sms"],
            value_field="name",
        ),
        FilterConditionFieldParam(
            field="place",
            label=gettext("Place"),
            operators=[
                FilterConditionOperator.MATCH,
                FilterConditionOperator.IN,
                FilterConditionOperator.NOT_IN,
            ],
            values=values["place"],
            value_field="qcode",
        ),
        FilterConditionFieldParam(
            field="ingest_provider",
            label=gettext("Ingest provider"),
            operators=[FilterConditionOperator.EQUALS, FilterConditionOperator.NOT_EQUALS],
            values=values["ingest_provider"],
            value_field="_id",
        ),
        FilterConditionFieldParam(
            field="embargo",
            label=gettext("Embargo"),
            operators=[FilterConditionOperator.EQUALS, FilterConditionOperator.NOT_EQUALS],
            values=values["embargo"],
            value_field="name",
        ),
        FilterConditionFieldParam(
            field="featuremedia",
            label=gettext("Feature Media"),
            operators=[FilterConditionOperator.EXISTS],
            values=values["featuremedia"],
            value_field="name",
        ),
        FilterConditionFieldParam(
            field="anpa_take_key",
            operators=[
                FilterConditionOperator.IN,
                FilterConditionOperator.NOT_IN,
                FilterConditionOperator.EQUALS,
                FilterConditionOperator.NOT_EQUALS,
                FilterConditionOperator.LIKE,
                FilterConditionOperator.NOT_LIKE,
                FilterConditionOperator.STARTS_WITH,
                FilterConditionOperator.ENDS_WITH,
            ],
        ),
    ]

    fields.extend(await _get_vocabulary_fields(values))
    await on_get_available_filter_params.send(fields)
    return fields


async def _get_vocabulary_fields(values: dict[str, list[str] | list[dict]]) -> list[FilterConditionFieldParam]:
    excluded_vocabularies = copy(get_config(list[str], "EXCLUDED_VOCABULARY_FIELDS"))
    excluded_vocabularies.extend(values.keys())
    lookup = {"_id": {"$nin": excluded_vocabularies}, "type": "manageable"}
    fields: list[FilterConditionFieldParam] = []

    async for vocabulary in await VocabulariesResourceModel.get_service().search(lookup):
        if vocabulary.field_type and vocabulary.field_type != "text":
            continue

        field = FilterConditionFieldParam(
            field=vocabulary.id,
            label=vocabulary.display_name,
            operators=[
                FilterConditionOperator.IN,
                FilterConditionOperator.NOT_IN,
                FilterConditionOperator.EQUALS,
                FilterConditionOperator.NOT_EQUALS,
                FilterConditionOperator.LIKE,
                FilterConditionOperator.NOT_LIKE,
                FilterConditionOperator.STARTS_WITH,
                FilterConditionOperator.ENDS_WITH,
            ]
            if vocabulary.field_type == "text"
            else [
                FilterConditionOperator.IN,
                FilterConditionOperator.NOT_IN,
            ],
        )

        if vocabulary.field_type != "text":
            field.values = [item.to_dict() for item in vocabulary.items]
            field.value_field = "qcode"

        fields.append(field)

    return fields


async def _get_field_values() -> dict[str, list[str] | list[dict]]:
    values: dict[str, list[str] | list[dict]] = {}
    vocabularies_resource = VocabulariesResourceModel.get_service()
    categories_cv = await vocabularies_resource.find_by_id_raw("categories")
    values["anpa_category"] = cast(list[dict], categories_cv.get("items") if categories_cv else [])
    genre_cursor = await vocabularies_resource.search({"$or": [{"schema_field": "genre"}, {"_id": "genre"}]})
    genre = await genre_cursor.next_raw()
    if genre:
        values["genre"] = genre["items"]
    for voc_id in ("urgency", "priority", "type"):
        try:
            vocabulary = await vocabularies_resource.find_by_id_raw(voc_id)
            values[voc_id] = vocabulary["items"] if vocabulary else []
        except TypeError:
            values[voc_id] = []
    subject_cursor = await vocabularies_resource.search({"schema_field": "subject"})
    subject = await subject_cursor.next_raw()
    if subject:
        values["subject"] = cast(list[dict], subject["items"])
    else:
        values["subject"] = get_subjectcodeitems()

    desks = await DesksResourceModel.get_service().get_all_list_raw()
    values["desk"] = desks
    values["stage"] = await _get_stage_field_values(desks)
    values["sms"] = [{"qcode": 0, "name": "False"}, {"qcode": 1, "name": "True"}]
    values["embargo"] = [{"qcode": 0, "name": "False"}, {"qcode": 1, "name": "True"}]
    place_cursor = await vocabularies_resource.search(
        {"$or": [{"schema_field": "place"}, {"_id": "place"}, {"_id": "locators"}]}
    )
    place = await place_cursor.next_raw()
    values["place"] = place["items"] if place else []
    values["ingest_provider"] = await (await get_resource_service("ingest_providers").get_async(None, {})).to_list()
    values["featuremedia"] = [{"qcode": 1, "name": "True"}, {"qcode": 0, "name": "False"}]
    return values


async def _get_stage_field_values(desks: list[dict]) -> list[dict]:
    # TODO-ASYNC: Convert this to use async stages service
    stages = list(get_resource_service("stages").get(None, {}))
    for i, stage in enumerate(stages):
        try:
            desk = next(filter(lambda d: d["_id"] == stage["desk"], desks))
        except (StopIteration, KeyError):
            # if stage has no desk, remove that stage from a list
            logger.warning("Desk not found for stage", extra=dict(stage_id=stage.get("_id")))
            stages[i] = None
            continue
        stages[i]["name"] = "{}: {}".format(desk["name"], stage["name"])
    return list(i for i in stages if i)
