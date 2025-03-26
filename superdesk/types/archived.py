# This file is part of Superdesk
#
# Copyright 2013, 2025 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from datetime import datetime
from enum import Enum

from pydantic import Field

from superdesk.core.resources import fields
from superdesk.types.archive import ArchiveResourceModel


class QueueState(Enum):
    PENDING = "pending"
    PUSHED = "pushed"
    IN_PROGRESS = "in_progress"
    QUEUED = "queued"
    QUEUED_NOT_TRANSMITTED = "queued_not_transmitted"
    ERROR = "error"


class ArchivedResourceModel(ArchiveResourceModel):
    item_id: fields.Keyword
    last_published_version: bool = True
    queue_state: QueueState = QueueState.PENDING
    error_message: str = ""
    is_take_item: bool = Field(False, deprecated=True)
    digital_item_id: str = Field("", deprecated=True)
    # FIXME: readonly
    publish_sequence_no: int
    last_queue_event: datetime
    moved_to_legal: bool = False
    # if item is published as part of a package this will
    # be set to package id so transmitter can handle such
    # items differently
    published_in_package: str
    # must be set explicitly, there is no versioning
    _current_version: int
    archived_id: str | None = None
