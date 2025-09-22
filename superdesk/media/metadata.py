from typing import overload, Literal

from superdesk.types import Item

from superdesk.metadata.item import CONTENT_TYPE_LITERAL
from superdesk.media.image import (
    PhotoMetadataMapping,
    PhotoMetadata,
    read_metadata as image_read_metadata,
    write_metadata as image_write_metadata,
)
from superdesk.media.video import (
    read_metadata as video_read_metadata,
    get_video_from_photo,
    write_metadata as video_write_metadata,
    VideoMetadata,
)


def read_metadata(bin: bytes, content_type: CONTENT_TYPE_LITERAL):
    return video_read_metadata(bin) if content_type == "video" else image_read_metadata(bin)


def get_metadata_from_item(item: Item, mapping: PhotoMetadataMapping, content_type: CONTENT_TYPE_LITERAL):
    metadata = PhotoMetadata()
    for src, dest in mapping.items():
        value = get_item_value(item, src)
        if value is not None:
            metadata[dest] = value

    if content_type == "video":
        return get_video_from_photo(metadata)
    return metadata


def get_item_value(item, src: str):
    if src.startswith("extra."):
        extra = item.get("extra") or {}
        return extra.get(src[6:])
    return item.get(src)


@overload
def write_metadata(bin: bytes, metadata: VideoMetadata, content_type: Literal["video"]) -> bytes:
    ...  # noqa


@overload
def write_metadata(bin: bytes, metadata: PhotoMetadata, content_type: Literal["picture"]) -> bytes:
    ...  # noqa


def write_metadata(bin: bytes, metadata, content_type: CONTENT_TYPE_LITERAL):
    return video_write_metadata(bin, metadata) if content_type == "video" else image_write_metadata(bin, metadata)
