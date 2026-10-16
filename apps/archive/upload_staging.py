# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2026 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

"""Upload staging.

Lets a client send a media binary ahead of creating an archive item. The binary is stored,
workers extract embedded metadata (IPTC/XMP), and the client then either commits the upload
by posting to ``archive`` with ``staged_id`` or discards it.
Workers persist metadata and rendition status here, without using a Celery results backend.
Expired uploads are removed by a scheduled task so their media can be cleaned up too.
"""

import logging
import asyncio
from contextlib import ExitStack
from datetime import timedelta
from tempfile import NamedTemporaryFile
from typing import Any, IO
from uuid import uuid4

from celery import shared_task
from eve.methods.common import resolve_document_etag
from quart_babel import gettext as _

import superdesk
from superdesk.core import get_app_config, get_current_app
from superdesk.eve_async import AsyncBaseService
from superdesk.errors import SuperdeskApiError
from superdesk.filemeta import set_filemeta
from superdesk.media.media_operations import process_file, encode_metadata, decode_metadata
from superdesk.media.metadata import read_metadata
from superdesk.media.renditions import create_renditions_for_file, get_renditions_spec_async
from superdesk.media.video_editor import VideoEditorWrapper
from superdesk.metadata.item import CONTENT_TYPE_LITERAL
from superdesk.resource import Resource
from superdesk.utc import utcnow
from superdesk.notification import push_notification
from apps.auth import get_user

logger = logging.getLogger(__name__)

STAGEABLE_FILE_TYPES: dict[str, CONTENT_TYPE_LITERAL] = {
    "image": "picture",
    "audio": "audio",
    "video": "video",
}

#: article field -> embedded metadata key, can be extended using ``PICTURE_METADATA_MAPPING``
DEFAULT_METADATA_MAPPING = {
    "byline": "Creator",
    "headline": "Headline",
    "description_text": "Description",
    "copyrightnotice": "CopyrightNotice",
    "creditline": "CreditLine",
}


def map_metadata_to_article(raw_metadata: dict[str, Any], user: dict[str, Any] | None = None) -> dict[str, Any]:
    """Map embedded media metadata to article fields."""
    mapping = {**DEFAULT_METADATA_MAPPING, **(get_app_config("PICTURE_METADATA_MAPPING") or {})}
    meta: dict[str, Any] = {}

    for field, key in mapping.items():
        value = raw_metadata.get(key)
        if isinstance(value, list):
            value = ", ".join(str(v) for v in value if v)
        if value in (None, ""):
            continue
        if field.startswith("extra."):
            meta.setdefault("extra", {})[field[len("extra.") :]] = value
        else:
            meta[field] = value

    if not meta.get("byline") and user and user.get("byline"):
        meta["byline"] = user["byline"]

    return meta


class UploadStagingResource(Resource):
    schema = {
        "media": {"type": "file"},
        "filename": {"type": "string", "readonly": True},
        "mimetype": {"type": "string", "readonly": True},
        "size": {"type": "integer", "readonly": True},
        "meta": {"type": "dict", "allow_unknown": True, "readonly": True},
        "raw_metadata": {"type": "dict", "allow_unknown": True, "readonly": True},
        "filemeta": {"type": "dict", "allow_unknown": True, "readonly": True},
        "filemeta_json": {"type": "string", "readonly": True},
        "status": {
            "type": "string",
            "allowed": [
                "pending",
                "processing",
                "awaiting_confirmation",
                "ready",
                "failed",
                "committing",
                "discarded",
                "consumed",
            ],
            "readonly": True,
        },
        "error": {"type": "string", "readonly": True},
        "metadata_status": {"type": "string", "readonly": True},
        "metadata_error": {"type": "string", "readonly": True},
        "confirmed": {"type": "boolean", "default": False},
        "renditions": {"type": "dict", "allow_unknown": True, "readonly": True},
        "video_server_id": {"type": "string", "readonly": True},
        "archive_id": {"type": "string", "readonly": True},
        "user": Resource.rel("users", embeddable=False, readonly=True),
        "expires": {"type": "datetime", "readonly": True},
    }
    datasource = {
        "projection": {
            "filename": 1,
            "mimetype": 1,
            "size": 1,
            "meta": 1,
            "raw_metadata": 1,
            "filemeta": 1,
            "filemeta_json": 1,
            "status": 1,
            "error": 1,
            "metadata_status": 1,
            "metadata_error": 1,
            "confirmed": 1,
            "renditions": 1,
            "video_server_id": 1,
            "archive_id": 1,
            "user": 1,
            "expires": 1,
            "media": 1,
            "_created": 1,
            "_updated": 1,
            "_etag": 1,
        }
    }
    resource_methods = ["POST"]
    item_methods = ["GET", "PATCH", "DELETE"]
    privileges = {"POST": "archive", "PATCH": "archive", "DELETE": "archive"}
    mongo_indexes = {
        "expires_1": ([("expires", 1)], {"background": True}),
        "archive_id_1": ([("archive_id", 1)], {"background": True, "sparse": True}),
    }


class UploadStagingService(AsyncBaseService):
    async def update_processing(self, query: dict, updates: dict) -> dict | None:
        """Atomically publish worker changes with fresh HTTP cache validators."""
        for _attempt in range(5):
            original = await self.find_one_async(req=None, **query)
            if original is None:
                return None
            changes = {**updates, "_updated": utcnow(microseconds=True)}
            updated = {**original, **changes}
            resolve_document_etag(updated, self.datasource)
            if "_etag" in updated:
                changes["_etag"] = updated["_etag"]
            matched = await self.find_and_modify_async(
                {"$and": [{**query, "_id": original["_id"]}, {"_etag": original.get("_etag")}]},
                {"$set": changes},
            )
            if matched is not None:
                return matched
        raise SuperdeskApiError.conflictError(_("Staged upload changed while processing"))

    async def on_create_async(self, docs):
        app = get_current_app()
        user = get_user(required=True)

        for doc in docs:
            content = doc.get("media")
            if content is None:
                raise SuperdeskApiError.badRequestError(_("No media found"))

            content_type = app.media._get_mimetype(content)
            content.seek(0)
            file_type = content_type.split("/")[0]
            if file_type not in STAGEABLE_FILE_TYPES:
                raise SuperdeskApiError.badRequestError(_("Unsupported media type"))

            content.seek(0, 2)
            size = content.tell()
            content.seek(0)
            file_name = uuid4().hex
            upload_name = getattr(content, "filename", None) or file_name
            doc["media"] = await app.media.put_async(
                content, filename=file_name, content_type=content_type, metadata={"length": str(size)}
            )

            doc["filename"] = upload_name
            doc["mimetype"] = content_type
            doc["size"] = size
            doc["meta"] = map_metadata_to_article({}, user)
            doc["metadata_status"] = "pending"
            doc["user"] = user["_id"]
            doc["expires"] = utcnow() + timedelta(seconds=get_app_config("UPLOAD_STAGING_TTL"))
            doc["status"] = "pending"

    async def on_created_async(self, docs):
        for doc in docs:
            try:
                await process_staged_upload.delay(doc["_id"])
            except Exception:
                logger.exception("Failed to queue staged upload %s", doc["_id"])
                await self.update_processing(
                    {"_id": doc["_id"], "status": "pending"},
                    {"status": "failed", "error": str(_("Failed to queue media processing"))},
                )
                raise
            # Eager execution (tests/development) may already have finished processing.
            current = await self.find_one_async(req=None, _id=doc["_id"])
            if not current:
                raise SuperdeskApiError.notFoundError(_("Staged upload not found or expired"))
            doc.update(current)

    async def on_update_async(self, updates, original):
        self._check_owner(original)
        if updates.get("confirmed") is not True or original["expires"] <= utcnow():
            raise SuperdeskApiError.badRequestError(_("Only upload confirmation is allowed"))

    async def on_updated_async(self, updates, original):
        if updates.get("confirmed"):
            await process_staged_upload.delay(original["_id"], renditions_only=True)

    async def on_fetched_item_async(self, doc):
        self._check_owner(doc)
        if doc["expires"] <= utcnow() or doc["status"] in ("discarded", "consumed"):
            raise SuperdeskApiError.notFoundError(_("Staged upload not found or expired"))

    async def on_delete_async(self, doc):
        self._check_owner(doc)
        if not await self.discard(doc["_id"]):
            raise SuperdeskApiError.conflictError(_("Staged upload is no longer available"))

    async def discard(self, staged_id) -> bool:
        staged = await self.update_processing(
            {"_id": staged_id, "status": {"$nin": ["committing", "consumed"]}},
            {"status": "discarded"},
        )
        if not staged:
            return False
        await delete_staged_media(staged)
        return True

    async def finish_commit(self, staged: dict) -> None:
        """Release staging only after the archive item has been persisted."""
        if staged["status"] != "consumed":
            claimed = await self.update_processing(
                {"_id": staged["_id"], "status": "committing", "archive_id": staged["archive_id"]},
                {"status": "consumed"},
            )
            if not claimed:
                return
        if staged.get("video_server_id"):
            await get_current_app().media.delete_async(staged["media"])
        await self.delete_async({"_id": staged["_id"], "status": "consumed"})

    @staticmethod
    def _check_owner(doc):
        if str(doc.get("user")) != str(get_user(required=True)["_id"]):
            raise SuperdeskApiError.forbiddenError(_("Staged upload belongs to another user"))


async def delete_staged_media(staged: dict, *, original: bool = True) -> None:
    media_ids = {rend["media"] for rend in staged.get("renditions", {}).values() if rend.get("media")}
    if original:
        media_ids.add(staged["media"])
    else:
        media_ids.discard(staged["media"])
    for media_id in media_ids:
        await get_current_app().media.delete_async(media_id)
    if staged.get("video_server_id"):
        VideoEditorWrapper()._delete(staged["video_server_id"])


def notify_staged_upload(staged: dict) -> None:
    push_notification("upload_staging:updated", staged_id=str(staged["_id"]), user=str(staged["user"]))


async def extract_staged_metadata(staged: dict, content: IO[bytes], path: str) -> dict:
    file_type = staged["mimetype"].split("/")[0]
    updates = {"metadata_status": "ready"}

    def parse():
        try:
            raw = {} if file_type == "audio" else dict(read_metadata(path, STAGEABLE_FILE_TYPES[file_type]))
            mapping_input = raw.copy()
            if file_type == "video":
                for canonical, alias in (("CopyrightNotice", "Rights"), ("CreditLine", "Credit")):
                    if alias in raw:
                        mapping_input.setdefault(canonical, raw[alias])
            return {"raw_metadata": raw, "meta": map_metadata_to_article(mapping_input, staged.get("meta"))}
        except Exception:
            logger.exception("Failed to extract embedded metadata for %s", staged["_id"])
            return {
                "metadata_status": "failed",
                "metadata_error": str(_("Metadata extraction failed. Enter metadata manually.")),
            }

    updates.update(await asyncio.to_thread(parse))
    content.seek(0)
    metadata = await asyncio.to_thread(process_file, content, file_type)
    metadata["length"] = staged["size"]
    set_filemeta(updates, decode_metadata(encode_metadata(metadata)))
    return updates


@shared_task(ignore_result=True, store_async_result=False)
async def process_staged_upload(staged_id, renditions_only: bool = False) -> None:
    service = superdesk.get_resource_service("upload_staging")
    staged = await service.update_processing(
        {
            "_id": staged_id,
            "status": "awaiting_confirmation" if renditions_only else "pending",
            "expires": {"$gt": utcnow()},
            **({"confirmed": True} if renditions_only else {}),
        },
        {"status": "processing"},
    )
    if not staged:
        return

    files = ExitStack()
    original_content = None
    try:
        file_type = staged["mimetype"].split("/")[0]
        if not renditions_only:
            media = await get_current_app().media.get_async(staged["media"])
            if not media:
                raise SuperdeskApiError.notFoundError(_("Staged media not found"))
            tmp = files.enter_context(NamedTemporaryFile(suffix="." + staged["mimetype"].split("/")[1]))
            async with media:
                async for chunk in media:
                    tmp.write(chunk)
            tmp.flush()
            original_content = tmp.file
            metadata_updates = await extract_staged_metadata(staged, original_content, tmp.name)
            current = await service.update_processing(
                {"_id": staged_id, "status": "processing", "expires": {"$gt": utcnow()}},
                metadata_updates,
            )
            if not current:
                return
            staged.update(metadata_updates)
            notify_staged_upload(staged)
            if file_type == "video":
                waiting = await service.update_processing(
                    {"_id": staged_id, "status": "processing"},
                    {"status": "awaiting_confirmation"},
                )
                if waiting:
                    notify_staged_upload(staged)
                    current = await service.find_one_async(None, _id=staged_id)
                    if current and current.get("confirmed"):
                        await process_staged_upload.delay(staged_id, renditions_only=True)
                return
        if file_type == "video" and get_app_config("VIDEO_SERVER_ENABLED"):
            from .archive_media import ArchiveMediaService

            media_service = ArchiveMediaService()
            doc = {"media_fetched": await get_current_app().media.get_async(staged["media"])}
            await media_service._load_staged_binary(doc, staged)
            binary = doc["media"]
            try:
                res, renditions, metadata = media_service.upload_file_to_video_server(doc)
                staged["video_server_id"] = res["_id"]
                media_service.video_editor.create_timeline_thumbnails(doc["media"], 60)
            finally:
                binary.close()
            set_filemeta(staged, metadata)
        else:
            specs = await get_renditions_spec_async(no_custom_crops=get_app_config("NO_CUSTOM_CROPS"))
            renditions = await create_renditions_for_file(
                staged["media"],
                specs,
                file_type,
                delete_all_on_error=True,
                content_type=staged["mimetype"],
                original_content=original_content,
            )
        staged["renditions"] = renditions
        updates = {key: staged[key] for key in ("renditions", "video_server_id", "filemeta_json") if key in staged}
        updates["status"] = "ready"
        published = await service.update_processing(
            {"_id": staged_id, "status": "processing", "expires": {"$gt": utcnow()}},
            updates,
        )
        if not published:
            # Discard/expiry may race with processing; never leave the worker's output orphaned.
            await delete_staged_media(staged, original=False)
        else:
            notify_staged_upload(staged)
    except (Exception, asyncio.CancelledError):
        logger.exception("Failed to process staged upload %s", staged_id)
        await delete_staged_media(staged, original=False)
        await service.update_processing(
            {"_id": staged_id, "status": "processing"},
            {"status": "failed", "error": str(_("Media processing failed. Remove the file and try again."))},
        )
        notify_staged_upload(staged)
        raise
    finally:
        files.close()


@shared_task(ignore_result=True, store_async_result=False)
async def expire_staged_uploads() -> None:
    service = superdesk.get_resource_service("upload_staging")
    async for staged in await service.find_async({"expires": {"$lte": utcnow()}}):
        if staged["status"] in ("committing", "consumed"):
            archive = await superdesk.get_resource_service("archive").find_one_async(None, _id=staged["archive_id"])
            if archive or staged["status"] == "consumed":
                await service.finish_commit(staged)
                continue
            expired = await service.update_processing(
                {"_id": staged["_id"], "status": "committing", "expires": {"$lte": utcnow()}},
                {"status": "discarded"},
            )
            if expired:
                await delete_staged_media(expired)
                await service.delete_async({"_id": staged["_id"], "status": "discarded"})
            continue
        if await service.discard(staged["_id"]):
            await service.delete_async({"_id": staged["_id"], "status": "discarded"})


def init_app(app) -> None:
    endpoint_name = "upload_staging"
    service = UploadStagingService(endpoint_name, backend=superdesk.get_backend())
    UploadStagingResource(endpoint_name, app=app, service=service)
