from typing import overload, Literal

from superdesk.types import Item

from superdesk.media.metadata_mapping import Metadata, MetadataMapping
from superdesk.metadata.item import CONTENT_TYPE_LITERAL
from superdesk.media.image import (
    read_metadata as image_read_metadata,
    write_metadata as image_write_metadata,
)
from superdesk.media.video import (
    read_metadata as video_read_metadata,
    get_video_from_photo,
    write_metadata as video_write_metadata,
)


def read_metadata(bin: bytes, content_type: CONTENT_TYPE_LITERAL) -> Metadata:
    return video_read_metadata(bin) if content_type == "video" else image_read_metadata(bin)


def get_metadata_from_item(item: Item, mapping: MetadataMapping, content_type: CONTENT_TYPE_LITERAL) -> Metadata:
    metadata = Metadata()
    for src, dest in mapping.items():
        value = _get_item_value(item, src)
        if value is not None:
            metadata[dest] = value

    if content_type == "video":
        return get_video_from_photo(metadata)
    return metadata


def _get_item_value(item, src: str) -> str | None:
    if src.startswith("extra."):
        extra = item.get("extra") or {}
        return extra.get(src[6:])
    return item.get(src)


@overload
def write_metadata(bin: bytes, metadata: Metadata, content_type: Literal["video"]) -> bytes:
    ...  # noqa


@overload
def write_metadata(bin: bytes, metadata: Metadata, content_type: Literal["picture"]) -> bytes:
    ...  # noqa


def write_metadata(bin: bytes, metadata, content_type: CONTENT_TYPE_LITERAL):
    return video_write_metadata(bin, metadata) if content_type == "video" else image_write_metadata(bin, metadata)
