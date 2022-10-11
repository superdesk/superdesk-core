from typing import List
from datetime import datetime, timedelta

from .. import types


def item_title(show: types.IShow, rundown: types.IRundown, item: types.IRundownItem) -> str:
    return "-".join(
        filter(
            None,
            [
                item.get("item_type", "").upper(),
                show.get("shortcode", "").upper(),
                (item.get("title") or "").upper(),
            ],
        )
    )


def format_duration(duration) -> str:
    if duration:
        delta = timedelta(seconds=int(duration))
        return (datetime(year=1, month=1, day=1) + delta).strftime("%H:%M:%S")
    return ""


def item_table_data(show: types.IShow, rundown: types.IRundown, item: types.IRundownItem, order: int) -> List[str]:
    return [
        str(order),
        item["item_type"].upper(),
        item_title(show, rundown, item),
        "Tone" if item.get("live_sound") else "OFF",
        item.get("additional_notes") or "",
        item.get("live_captions") or "",
        item.get("last_sentence") or "",
        format_duration(item.get("duration")),
    ]
