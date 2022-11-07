from typing import List
from datetime import datetime, timedelta

from superdesk.text_utils import get_text
from superdesk.editor_utils import get_field_content_state

from .. import types, utils as rundown_utils


def to_string(item, key) -> str:
    return item.get(key) or ""


def format_duration(duration) -> str:
    if duration:
        delta = timedelta(seconds=int(duration))
        return (datetime(year=1, month=1, day=1) + delta).strftime("%H:%M:%S")
    return ""


def item_table_data(show: types.IShow, rundown: types.IRundown, item: types.IRundownItem, order: int) -> List[str]:
    return [
        str(order),
        to_string(item, "item_type").upper(),
        rundown_utils.item_title(show, rundown, item),
        to_string(item, "additional_notes"),
        format_duration(item.get("duration")),
    ]
