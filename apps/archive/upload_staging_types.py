"""Shared document types for staged upload processing and archive commits."""

from datetime import datetime
from enum import Enum, unique
from typing import Any, Literal, NotRequired, TypedDict

from werkzeug.datastructures import FileStorage

from superdesk.core.types import SuperdeskAsyncFile
from superdesk.types import Id


@unique
class UploadStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    READY = "ready"
    FAILED = "failed"
    COMMITTING = "committing"
    DISCARDED = "discarded"
    CONSUMED = "consumed"


@unique
class MetadataStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    FAILED = "failed"


class StagedMediaInfo(TypedDict):
    mimetype: str
    filename: NotRequired[str]


class StagedMetadata(TypedDict, total=False):
    metadata_status: MetadataStatus
    metadata_error: str
    meta: dict[str, Any]
    raw_metadata: dict[str, Any]
    iptc_metadata: dict[str, Any]
    filemeta: dict[str, Any]
    filemeta_json: str


class StagedUpload(StagedMediaInfo, StagedMetadata):
    _id: Id
    media: str
    user: Id
    expires: datetime
    size: int
    status: UploadStatus
    confirmed: NotRequired[bool]
    processing_token: NotRequired[str]
    error: NotRequired[str]
    archive_id: NotRequired[str]
    video_server_id: NotRequired[str]
    renditions: NotRequired[dict[str, dict[str, Any]]]
    _etag: NotRequired[str]
    _created: NotRequired[datetime]
    _updated: NotRequired[datetime]


class ClaimedStagedUpload(StagedMediaInfo, StagedMetadata):
    """Worker output after the archive commit has claimed the staged upload."""

    _id: Id
    media: str
    user: Id
    expires: datetime
    status: Literal[UploadStatus.COMMITTING]
    archive_id: str
    video_server_id: NotRequired[str]
    error: NotRequired[str]
    renditions: dict[str, dict[str, Any]]


class StagedBinaryDocument(TypedDict):
    media_fetched: NotRequired[SuperdeskAsyncFile]
    media: NotRequired[FileStorage]
