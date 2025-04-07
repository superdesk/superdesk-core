from typing import cast
from bson import ObjectId

from superdesk.core import get_config
from superdesk.core.resources import ResourceCursorAsync
from superdesk.types import PublishQueueState, PublishQueueResource
from superdesk.utc import utcnow


def _get_queue_lookup(retries: bool = False, priority: bool | None = None) -> dict:
    priority_lookup = {"priority": priority if priority else {"$ne": True}}
    if retries:
        return {
            "$and": [
                {"state": PublishQueueState.RETRYING},
                {"next_retry_attempt_at": {"$lte": utcnow()}},
                priority_lookup,
            ]
        }
    return {
        "$and": [
            {"state": PublishQueueState.PENDING},
            priority_lookup,
        ]
    }


async def get_queue_items(
    retries: bool = False, subscriber_id: ObjectId | None = None, priority: bool | None = None
) -> ResourceCursorAsync[PublishQueueResource]:
    lookup = _get_queue_lookup(retries, priority)
    if subscriber_id:
        lookup["$and"].append({"subscriber_id": subscriber_id})

    return await PublishQueueResource.get_service().find(
        lookup,
        max_results=cast(int, get_config(int, "MAX_TRANSMIT_QUERY_LIMIT")),  # limit per subscriber now
        sort=[("_created", 1), ("published_seq_num", 1)],
    )
