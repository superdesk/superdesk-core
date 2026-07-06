import asyncio
import logging

import aiohttp
from bson import ObjectId

from superdesk.json_utils import SuperdeskJSONEncoder

from superdesk.celery_app import celery
from superdesk.core.resources import AsyncResourceService
from superdesk.core.web import AsyncHttpClientSessionMixin

from .models import ContentListWebhook

logger = logging.getLogger(__name__)

WEBHOOK_MAX_RETRIES = 3
WEBHOOK_RETRY_COUNTDOWN = 60


class ContentListWebhooksService(AsyncResourceService[ContentListWebhook]):
    pass


class WebhookContentListDelivery(AsyncHttpClientSessionMixin):
    """Posts webhook payloads over the shared async HTTP client session."""

    http_timeout = aiohttp.ClientTimeout(connect=5, sock_read=10)

    async def post_list(self, url: str, payload: dict) -> None:
        # Encode the body ourselves: the Celery serializer re-casts hex-string
        # ids back into ObjectId on the worker, which json.dumps cannot
        # serialize. SuperdeskJSONEncoder renders ObjectId and datetime
        # (ISO-8601). Must go through ``data=`` — aiohttp's ``json=`` would
        # re-serialize the already-encoded string into a JSON string literal.
        body = SuperdeskJSONEncoder().encode(payload)
        http_client = await self.http_session()
        async with http_client.post(url, data=body, headers={"Content-Type": "application/json"}) as response:
            response.raise_for_status()


async def enqueue_webhook_deliveries(event: str, list_id: ObjectId) -> None:
    """Queue a delivery for each enabled webhook that does not exclude this list.

    Reads matching webhooks in the request's async context, then hands each
    delivery off to a Celery task so the slow outbound HTTP never blocks the
    API request that triggered the change.

    Never raises: by the time this runs the triggering change is already
    committed, so a broker outage must not fail the request — the error is
    logged and the deliveries are dropped.
    """
    try:
        webhooks = await ContentListWebhooksService().get_all_list({"enabled": True})
        payload = {"event": event, "list_id": str(list_id)}
        for webhook in webhooks:
            if list_id in webhook.excluded_lists:
                continue
            await deliver_content_list_webhook.apply_async(kwargs={"url": webhook.url, "payload": payload})
    except Exception:
        logger.exception("Failed to enqueue content list webhook deliveries for list %s", list_id)


@celery.task(bind=True, max_retries=WEBHOOK_MAX_RETRIES, soft_time_limit=30)
async def deliver_content_list_webhook(self, url: str, payload: dict) -> None:
    """POST the change payload to a single webhook URL, retrying on failure.

    One task per webhook keeps retries isolated: a failing endpoint never
    causes a re-POST to endpoints that already succeeded. After the retries
    are exhausted the failure is logged and dropped.
    """
    try:
        await WebhookContentListDelivery().post_list(url, payload)
    except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=WEBHOOK_RETRY_COUNTDOWN)
        logger.error(
            "Content list webhook delivery to %s failed after %d retries: %s",
            url,
            self.max_retries,
            exc,
        )
