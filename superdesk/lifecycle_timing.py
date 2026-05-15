# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from datetime import datetime

from superdesk.utc import utcnow


def duration_ms(started: datetime, finished: datetime) -> int:
    return max(0, int((finished - started).total_seconds() * 1000))


def to_epoch_ms(value: datetime) -> int:
    return int(value.timestamp() * 1000)


def duration_ms_from_epoch(started_ms: int, finished_ms: int) -> int:
    return max(0, finished_ms - started_ms)


def ensure_lifecycle_timing(item: dict) -> dict:
    timing = item.get("lifecycle_timing")
    if not isinstance(timing, dict):
        timing = {}
        item["lifecycle_timing"] = timing
    return timing


def set_lifecycle_started_at(item: dict, started_at: datetime | None = None) -> datetime:
    timing = ensure_lifecycle_timing(item)
    started = timing.setdefault("lifecycle_started_at", started_at or utcnow(microseconds=True))
    timing.setdefault("lifecycle_started_ms", to_epoch_ms(started))
    return started


def set_ingest_started_at(item: dict, started_at: datetime | None = None) -> datetime:
    return set_lifecycle_started_at(item, started_at)


def set_ingest_finished_at(item: dict, finished_at: datetime | None = None) -> datetime:
    timing = ensure_lifecycle_timing(item)
    finished = finished_at or utcnow(microseconds=True)
    timing["ingest_finished_at"] = finished
    timing["ingest_finished_ms"] = to_epoch_ms(finished)

    started_ms = timing.get("lifecycle_started_ms")
    if isinstance(started_ms, int):
        timing["ingest_processing_ms"] = duration_ms_from_epoch(started_ms, timing["ingest_finished_ms"])
    else:
        started = timing.get("lifecycle_started_at")
        if started:
            timing["ingest_processing_ms"] = duration_ms(started, finished)

    return finished
