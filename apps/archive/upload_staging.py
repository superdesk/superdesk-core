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
workers extract embedded metadata (IPTC/XMP), and the client can commit the upload
by posting to ``archive`` with ``staged_id``. Abandoned uploads remain until expiry.
Workers persist metadata and rendition status here, without using a Celery results backend.
Expired uploads are removed by a scheduled task so their media can be cleaned up too.
"""

import logging
import asyncio
from contextlib import ExitStack
from collections.abc import Mapping
from datetime import timedelta
from tempfile import NamedTemporaryFile
from time import monotonic
from uuid import uuid4
from typing import Any, cast

from celery import shared_task
from eve.methods.common import resolve_document_etag
from pymongo import ReturnDocument
from quart_babel import gettext as _

import superdesk
from superdesk.core import get_config, get_current_app
from superdesk.types import Id
from superdesk.eve_async import AsyncBaseService
from superdesk.errors import SuperdeskApiError
from superdesk.filemeta import set_filemeta
from superdesk.media.renditions import create_renditions_for_file, get_renditions_spec_async
from superdesk.resource import Resource
from superdesk.utc import utcnow
from superdesk.notification import push_notification
from apps.auth import get_user
from .upload_staging_types import MetadataStatus, StagedBinaryDocument, StagedUpload, UploadStatus
from .upload_staging_processing import (
    STAGEABLE_FILE_TYPES,
    map_metadata_to_article,
    delete_staged_media,
    extract_staged_metadata,
)

logger = logging.getLogger(__name__)


class UploadStagingResource(Resource):
    schema = {
        "media": {"type": "file"},
        "filename": {"type": "string", "readonly": True},
        "mimetype": {"type": "string", "readonly": True},
        "size": {"type": "integer", "readonly": True},
        "meta": {"type": "dict", "allow_unknown": True, "readonly": True},
        "raw_metadata": {"type": "dict", "allow_unknown": True, "readonly": True},
        "iptc_metadata": {"type": "dict", "allow_unknown": True, "readonly": True},
        "filemeta": {"type": "dict", "allow_unknown": True, "readonly": True},
        "filemeta_json": {"type": "string", "readonly": True},
        "status": {
            "type": "string",
            "allowed": [status.value for status in UploadStatus],
            "readonly": True,
        },
        "error": {"type": "string", "readonly": True},
        "processing_token": {"type": "string", "readonly": True},
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
            "iptc_metadata": 1,
            "filemeta": 1,
            "filemeta_json": 1,
            "status": 1,
            "error": 1,
            "processing_token": 1,
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
    item_methods = ["GET", "PATCH"]
    privileges = {"POST": "archive", "PATCH": "archive"}
    mongo_indexes = {
        "expires_1": ([("expires", 1)], {"background": True}),
        "archive_id_1": ([("archive_id", 1)], {"background": True, "sparse": True}),
    }


class UploadStagingService(AsyncBaseService):
    async def update_processing(self, query: dict[str, Any], updates: Mapping[str, Any]) -> StagedUpload | None:
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
                return_document=ReturnDocument.AFTER,
            )
            if matched is not None:
                return cast(StagedUpload, matched)
        raise SuperdeskApiError.conflictError(_("Staged upload changed while processing"))

    async def on_create_async(self, docs: list[dict[str, Any]]) -> None:
        app = get_current_app()
        user = get_user(required=True)

        for doc in docs:
            started = monotonic()
            file_name = uuid4().hex
            logger.info("Staged upload received upload=%s; detecting media type", file_name)
            content = doc.get("media")
            if content is None:
                raise SuperdeskApiError.badRequestError(_("No media found"))

            upload_name = getattr(content, "filename", None)
            # libmagic only sniffs the first 16 KB, which can be all ID3 tag for mp3s with cover art,
            # so let it fall back to the file extension (`None` if that is unknown too)
            content_type = app.media._get_mimetype(content, upload_name) or "application/octet-stream"
            logger.info("Staged upload detected upload=%s mimetype=%s", file_name, content_type)
            content.seek(0)
            file_type = content_type.split("/")[0]
            if file_type not in STAGEABLE_FILE_TYPES:
                raise SuperdeskApiError.badRequestError(_("Unsupported media type"))

            content.seek(0, 2)
            size = content.tell()
            content.seek(0)
            upload_name = upload_name or file_name
            logger.info("Staged upload storing binary upload=%s size=%s", file_name, size)
            doc["media"] = await app.media.put_async(
                content, filename=file_name, content_type=content_type, metadata={"length": str(size)}
            )
            logger.info(
                "Staged upload stored binary upload=%s media=%s elapsed=%.3fs",
                file_name,
                doc["media"],
                monotonic() - started,
            )

            doc["filename"] = upload_name
            doc["mimetype"] = content_type
            doc["size"] = size
            doc["meta"] = map_metadata_to_article({}, user)
            doc["metadata_status"] = MetadataStatus.PENDING
            doc["user"] = user["_id"]
            doc["expires"] = utcnow() + timedelta(seconds=get_config(int, "UPLOAD_STAGING_TTL"))
            doc["status"] = UploadStatus.PENDING
            logger.info("Staged upload prepared for database insertion upload=%s media=%s", file_name, doc["media"])

    async def on_created_async(self, docs: list[dict[str, Any]]) -> None:
        for doc in docs:
            started = monotonic()
            logger.info("Staged upload persisted staged_id=%s media=%s; dispatching worker", doc["_id"], doc["media"])
            try:
                await process_staged_upload.delay(doc["_id"])
            except Exception:
                logger.exception("Failed to queue staged upload %s", doc["_id"])
                await self.update_processing(
                    {"_id": doc["_id"], "status": UploadStatus.PENDING},
                    {"status": UploadStatus.FAILED, "error": str(_("Failed to queue media processing"))},
                )
                raise
            logger.info(
                "Staged upload dispatched staged_id=%s elapsed=%.3fs; refreshing status",
                doc["_id"],
                monotonic() - started,
            )
            # Eager execution (tests/development) may already have finished processing.
            current = await self.find_one_async(req=None, _id=doc["_id"])
            if not current:
                raise SuperdeskApiError.notFoundError(_("Staged upload not found or expired"))
            doc.update(current)
            logger.info(
                "Staged upload response ready staged_id=%s status=%s elapsed=%.3fs",
                doc["_id"],
                doc["status"],
                monotonic() - started,
            )

    async def on_update_async(self, updates: dict[str, Any], original: dict[str, Any]) -> None:
        self._check_owner(original)
        if "media" in updates or updates.get("confirmed") is not True or original["expires"] <= utcnow():
            raise SuperdeskApiError.badRequestError(_("Only upload confirmation is allowed"))

    async def on_updated_async(self, updates: dict[str, Any], original: dict[str, Any]) -> None:
        if updates.get("confirmed"):
            await process_staged_upload.delay(original["_id"], renditions_only=True)

    async def on_fetched_item_async(self, doc: dict[str, Any]) -> None:
        self._check_owner(doc)
        if doc["expires"] <= utcnow() or doc["status"] in (UploadStatus.DISCARDED, UploadStatus.CONSUMED):
            raise SuperdeskApiError.notFoundError(_("Staged upload not found or expired"))

    async def finish_commit(self, staged: StagedUpload) -> None:
        """Release staging only after the archive item has been persisted."""
        if staged["status"] != UploadStatus.CONSUMED:
            claimed = await self.update_processing(
                {"_id": staged["_id"], "status": UploadStatus.COMMITTING, "archive_id": staged["archive_id"]},
                {"status": UploadStatus.CONSUMED},
            )
            if not claimed:
                return
        if staged.get("video_server_id"):
            await get_current_app().media.delete_async(staged["media"])
        await self.delete_async({"_id": staged["_id"], "status": UploadStatus.CONSUMED})

    @staticmethod
    def _check_owner(doc: Mapping[str, Any]) -> None:
        if str(doc.get("user")) != str(get_user(required=True)["_id"]):
            raise SuperdeskApiError.forbiddenError(_("Staged upload belongs to another user"))


def notify_staged_upload(staged: StagedUpload) -> None:
    push_notification("upload_staging:updated", staged_id=str(staged["_id"]), user=str(staged["user"]))


async def _recover_processing_failure(
    service: UploadStagingService, staged_id: Id, token: str, staged: StagedUpload | None
) -> None:
    owned_processing = {"_id": staged_id, "status": UploadStatus.PROCESSING, "processing_token": token}
    failure = {
        "status": UploadStatus.FAILED,
        "error": str(_("Media processing failed. Remove the file and try again.")),
    }
    current = None
    for attempt in range(2):
        try:
            current = await service.update_processing(owned_processing, failure)
        except (Exception, asyncio.CancelledError):
            logger.exception("Failed to claim cleanup for staged upload %s", staged_id)
            current = None
        if current is None:
            try:
                current = cast(StagedUpload | None, await service.find_one_async(req=None, _id=staged_id))
            except (Exception, asyncio.CancelledError):
                logger.exception("Failed to reconcile staged upload %s after processing failure", staged_id)
                continue
        if not current or current.get("processing_token") != token or current.get("status") != UploadStatus.PROCESSING:
            break

    if current and current.get("processing_token") == token:
        if current.get("status") == UploadStatus.FAILED:
            await delete_staged_media(staged or current, original=False)
        notify_staged_upload(current)


@shared_task(ignore_result=True, store_async_result=False, soft_time_limit=10 * 60, time_limit=15 * 60)
async def process_staged_upload(staged_id: Id, renditions_only: bool = False) -> None:
    started = monotonic()
    logger.info("Staged upload worker started staged_id=%s renditions_only=%s", staged_id, renditions_only)
    service = superdesk.get_resource_service("upload_staging")
    token = uuid4().hex
    owned_processing = {"_id": staged_id, "status": UploadStatus.PROCESSING, "processing_token": token}
    staged: StagedUpload | None = None
    files = ExitStack()
    original_content = None
    try:
        staged = await service.update_processing(
            {
                "_id": staged_id,
                "status": UploadStatus.AWAITING_CONFIRMATION if renditions_only else UploadStatus.PENDING,
                "expires": {"$gt": utcnow()},
                **({"confirmed": True} if renditions_only else {}),
            },
            {"status": UploadStatus.PROCESSING, "processing_token": token},
        )
        if not staged:
            logger.info("Staged upload worker skipped staged_id=%s; no eligible claim", staged_id)
            return
        file_type = staged["mimetype"].split("/")[0]
        if not renditions_only:
            logger.info("Staged upload worker downloading staged_id=%s media=%s", staged_id, staged["media"])
            media = await get_current_app().media.get_async(staged["media"])
            if not media:
                raise SuperdeskApiError.notFoundError(_("Staged media not found"))
            tmp = files.enter_context(NamedTemporaryFile(suffix="." + staged["mimetype"].split("/")[1]))
            async with media:
                async for chunk in media:
                    tmp.write(chunk)
            tmp.flush()
            original_content = tmp.file
            logger.info("Staged upload worker extracting metadata staged_id=%s", staged_id)
            metadata_updates = await extract_staged_metadata(staged, original_content, tmp.name)
            logger.info(
                "Staged upload worker extracted metadata staged_id=%s elapsed=%.3fs",
                staged_id,
                monotonic() - started,
            )
            current = await service.update_processing(
                {**owned_processing, "expires": {"$gt": utcnow()}},
                metadata_updates,
            )
            if not current:
                return
            staged.update(metadata_updates)
            notify_staged_upload(staged)
            if file_type == "video":
                waiting = await service.update_processing(
                    owned_processing,
                    {"status": UploadStatus.AWAITING_CONFIRMATION},
                )
                if waiting:
                    logger.info("Staged upload awaiting confirmation staged_id=%s", staged_id)
                    notify_staged_upload(staged)
                    current = await service.find_one_async(None, _id=staged_id)
                    if current and current.get("confirmed"):
                        await process_staged_upload.delay(staged_id, renditions_only=True)
                return
        logger.info("Staged upload worker generating renditions staged_id=%s", staged_id)
        if file_type == "video" and get_config(bool, "VIDEO_SERVER_ENABLED"):
            from .archive_media import ArchiveMediaService

            media_service = ArchiveMediaService()
            doc: StagedBinaryDocument = {"media_fetched": await get_current_app().media.get_async(staged["media"])}
            await media_service.load_staged_binary(doc, staged)
            binary = doc["media"]
            try:
                res, renditions, metadata = media_service.upload_file_to_video_server(doc)
                staged["video_server_id"] = res["_id"]
                media_service.video_editor.create_timeline_thumbnails(doc["media"], 60)
            finally:
                binary.close()
            set_filemeta(staged, metadata)
        else:
            specs = await get_renditions_spec_async(no_custom_crops=get_config(bool, "NO_CUSTOM_CROPS"))
            renditions = await create_renditions_for_file(
                staged["media"],
                specs,
                file_type,
                delete_all_on_error=True,
                temporary=False,
                content_type=staged["mimetype"],
                original_content=original_content,
            )
        staged["renditions"] = renditions
        updates = {
            key: value for key, value in staged.items() if key in ("renditions", "video_server_id", "filemeta_json")
        }
        updates["status"] = UploadStatus.READY
        published = await service.update_processing(
            {**owned_processing, "expires": {"$gt": utcnow()}},
            updates,
        )
        if not published:
            # Expiry may race with processing; never leave the worker's output orphaned.
            await delete_staged_media(staged, original=False)
        else:
            notify_staged_upload(staged)
            logger.info("Staged upload ready staged_id=%s elapsed=%.3fs", staged_id, monotonic() - started)
    except (Exception, asyncio.CancelledError):
        logger.exception("Failed to process staged upload %s", staged_id)
        await _recover_processing_failure(service, staged_id, token, staged)
        raise
    finally:
        files.close()


@shared_task(ignore_result=True, store_async_result=False)
async def expire_staged_uploads() -> None:
    service = superdesk.get_resource_service("upload_staging")
    async for staged in await service.find_async({"expires": {"$lte": utcnow()}}):
        if staged["status"] in (UploadStatus.COMMITTING, UploadStatus.CONSUMED):
            archive = await superdesk.get_resource_service("archive").find_one_async(None, _id=staged["archive_id"])
            if archive or staged["status"] == UploadStatus.CONSUMED:
                await service.finish_commit(staged)
                continue
        expired = await service.update_processing(
            {"_id": staged["_id"], "status": staged["status"], "expires": {"$lte": utcnow()}},
            {"status": UploadStatus.DISCARDED},
        )
        if expired:
            await delete_staged_media(expired)
            await service.delete_async({"_id": staged["_id"], "status": UploadStatus.DISCARDED})


def init_app(app) -> None:
    endpoint_name = "upload_staging"
    service = UploadStagingService(endpoint_name, backend=superdesk.get_backend())
    UploadStagingResource(endpoint_name, app=app, service=service)
