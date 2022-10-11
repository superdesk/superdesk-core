from typing import List
from datetime import datetime, timedelta

from superdesk.text_utils import get_text
from superdesk.editor_utils import get_field_content_state

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


def format_last_sentence(item) -> str:
    text = ""
    content_state = get_field_content_state(item, "content")
    if content_state:
        for block in content_state["blocks"]:
            if block.get("text"):
                text = block.get("text")
    elif item.get("content"):
        text = get_text(item["content"], "html", lf_on_block=True).strip()
    words = []
    for line in text.splitlines():
        for word in line.split():
            words.append(word)
    for i in range(-5, -1):
        output = " ".join(words[i:])
        if len(output) < 30:
            return output
    return ""


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
        format_last_sentence(item),
        format_duration(item.get("duration")),
    ]
