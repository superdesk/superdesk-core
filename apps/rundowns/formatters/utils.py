from typing import List

from .. import types


def item_title(show: types.IShow, rundown: types.IRundown, item: types.IRundownItem) -> str:
    return "-".join(
        filter(
            None,
            [
                item.get("item_type", "").upper(),
                show.get("shortcode", "").upper(),
                item.get("title", "").upper(),
            ],
        )
    )


def item_table_data(show: types.IShow, rundown: types.IRundown, item: types.IRundownItem, order: int) -> List[str]:
    return [
        str(order),
        item["item_type"].upper(),
        item_title(show, rundown, item),
        "Tone" if item.get("live_sound") else "OFF",
        item.get("additional_notes") or "",
        item.get("live_captions") or "",
        item.get("last_sentence") or "",
        str(item.get("duration", 0)),
    ]
