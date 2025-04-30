from typing import Any
from datetime import datetime

from superdesk.core import get_current_app
from superdesk.resource_fields import SCHEDULE_SETTINGS, PUBLISH_SCHEDULE


def get_subjectcodeitems():
    """Get subjects for current app."""
    return get_current_app().subjects.get_items()


def is_doc_targeted(item: dict, target: str | None = None) -> bool:
    """
    Determine if a given item dictionary includes targeted information.

    This function evaluates whether a specified target is present in the item
    dictionary or if any generic target-related fields contain data. It accepts
    an optional field name (target) to check for existence of information in
    that specific field, otherwise it defaults to checking multiple predefined
    keys in the item dictionary for any relevant content.

    :param item: A dictionary containing target-related data.
    :param target: Optional argument specifying the field to check for targeted information.
    :return: ``True`` if the targeted information is present in the specified field or default fields; ``False`` otherwise.
    """

    if target:
        return len(item.get(target, [])) > 0
    else:
        return (
            len(item.get("target_regions", []) + item.get("target_types", []) + item.get("target_subscribers", [])) > 0
        )


def get_codes(item: Any) -> set[str]:
    """
    Retrieve codes from an object attribute.

    This function attempts to extract and parse a 'codes' attribute from
    the provided object. The 'codes' attribute is expected to be a
    comma-separated string. Each code is stripped of whitespace, and
    only non-empty codes are included in the resulting set. If the
    provided object does not have a 'codes' attribute, the function
    returns an empty set.

    :param item: The object from which the 'codes' attribute is to be retrieved and parsed.
    :return: A set of unique, stripped codes. Returns an empty set if the 'codes' attribute is missing or empty.
    """

    try:
        codes: str = getattr(item, "codes", "") or ""
        return set([code.strip() for code in codes.split(",") if code.strip()])
    except AttributeError:
        return set()


def get_utc_publish_schedule(item):
    return item.get(SCHEDULE_SETTINGS, {}).get("utc_{}".format(PUBLISH_SCHEDULE))


def get_utc_schedule(doc, field_name) -> datetime | None:
    """Gets the utc value of the given field.

    :param doc: Article
    :param field_name: Name of he field: either publish_schedule or embargo
    :return: the utc value of the field
    """

    # TODO-ASYNC: Fix import here due to circular import
    from apps.archive.common import get_date, update_schedule_settings

    utc_field_name = "utc_{}".format(field_name)
    if (
        SCHEDULE_SETTINGS not in doc
        or not doc.get(SCHEDULE_SETTINGS)
        or utc_field_name not in doc.get(SCHEDULE_SETTINGS, {})
    ):
        update_schedule_settings(doc, field_name, doc.get(field_name))

    value = doc.get(SCHEDULE_SETTINGS, {}).get(utc_field_name)
    return get_date(value) if value else value
