from typing import List
from datetime import datetime, timedelta

from superdesk import get_resource_service

from .. import types, utils as rundown_utils


def to_string(item, key) -> str:
    return item.get(key) or ""


def format_duration(duration) -> str:
    if duration:
        delta = timedelta(seconds=int(duration))
        return (datetime(year=1, month=1, day=1) + delta).strftime("%H:%M:%S")
    return ""


def get_subitems() -> List[types.ISubject]:
    return get_resource_service("vocabularies").get_items("rundown_subitem_types")


def item_table_columns(subitems: List[types.ISubject]) -> List[str]:
    columns = [
        "Order",
        "Type",
        "Technical Title",
    ]

    for item in subitems:
        columns.append(item["name"])

    columns.extend(
        [
            "Additional realizer info",
            "Duration",
        ]
    )

    return columns


def item_table_data(
    show: types.IShow, rundown: types.IRundown, item: types.IRundownItem, order: int, subitems: List[types.ISubject]
) -> List[str]:
    data = [
        str(order),
        to_string(item, "item_type").upper(),
        rundown_utils.item_title(show, rundown, item),
    ]

    for subitem_type in subitems:
        if item.get("subitems"):
            for subitem in item["subitems"]:
                if subitem.get("qcode") == subitem_type["qcode"]:
                    data.append(subitem.get("technical_info") or "")
                    break
            else:
                data.append("")
        else:
            data.append("")

    data.extend(
        [
            to_string(item, "additional_notes"),
            format_duration(item.get("duration")),
        ]
    )

    return data
