# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import logging
from datetime import timedelta
from tempfile import TemporaryFile

from quart_babel import gettext as _
from werkzeug.datastructures import FileStorage

from superdesk import get_resource_service
from superdesk.core import get_current_app, get_app_config
from apps.auth import get_user
from superdesk.resource_fields import ID_FIELD, VERSION
from superdesk.flask import abort
from apps.archive.common import copy_metadata_from_user_preferences
from superdesk.media.media_operations import process_file_from_stream, decode_metadata
from superdesk.media.renditions import create_renditions_in_celery, get_renditions_spec_async
from superdesk.metadata.item import ITEM_STATE, CONTENT_STATE, ITEM_TYPE, CONTENT_TYPE
from .common import (
    update_dates_for,
    generate_guid,
    GUID_TAG,
    set_original_creator,
    generate_unique_id_and_name,
    set_item_expiry,
)
from superdesk.activity import add_activity
from superdesk.filemeta import set_filemeta, get_filemeta
from superdesk.errors import SuperdeskApiError
from superdesk.utc import utcnow
from superdesk.timer import timer
from superdesk.media.video_editor import VideoEditorWrapper

logger = logging.getLogger(__name__)


class ArchiveMediaService:
    video_editor = VideoEditorWrapper()

    type_av = {"image": CONTENT_TYPE.PICTURE, "audio": CONTENT_TYPE.AUDIO, "video": CONTENT_TYPE.VIDEO}

    async def on_create_async(self, docs):
        """Create corresponding item on file upload."""

        app = get_current_app()
        for doc in docs:
            res = None
            file_id: str | None = None
            delete_all_on_error = not doc.get("_import", None)
            staged = await self._pop_staged_upload(doc)

            if staged:
                content_type = staged["mimetype"]
            else:
                if "media" not in doc or doc["media"] is None:
                    abort(400, description=_("No media found"))
                # check content type of video by python-magic
                content_type = app.media._get_mimetype(doc["media"])
                doc["media"].seek(0)
            file_type = content_type.split("/")[0]
            if staged:
                renditions = staged["renditions"]
                metadata = get_filemeta(staged)
            elif file_type == "video" and get_app_config("VIDEO_SERVER_ENABLED"):
                # upload media to video server
                res, renditions, metadata = self.upload_file_to_video_server(doc)
                # get thumbnails for timeline bar
                self.video_editor.create_timeline_thumbnails(doc.get("media"), 60)
            else:
                file, content_type, metadata = await self.get_file_from_document(doc)
                file_id = doc["media"]
                # if no_custom_crops is set to False the custom crops are generated automatically on media upload
                # see (SDESK-4742)
                rendition_spec = await get_renditions_spec_async(no_custom_crops=get_app_config("NO_CUSTOM_CROPS"))
                with timer("archive:renditions"):
                    renditions = await create_renditions_in_celery(
                        file_id,
                        rendition_spec,
                        file_type,
                        # Don't delete files if we are on the import from storage flow
                        delete_all_on_error=delete_all_on_error,
                        content_type=content_type,
                    )
            try:
                await self._set_metadata(doc)
                doc[ITEM_TYPE] = self.type_av.get(file_type)
                doc[ITEM_STATE] = CONTENT_STATE.PROGRESS
                doc["renditions"] = renditions
                doc["mimetype"] = content_type
                set_filemeta(doc, metadata)
                await add_activity(
                    "upload",
                    "uploaded media {{ name }}",
                    "archive",
                    item=doc,
                    name=doc.get("headline", doc.get("mimetype")),
                    renditions=doc.get("renditions"),
                )
            except Exception as io:
                logger.exception(io)
                if delete_all_on_error and file_id:
                    await app.media.delete_async(file_id)
                if res:
                    self.video_editor._delete(res.get("_id"))
                abort(500)

    async def on_created_async(self, docs):
        service = get_resource_service("upload_staging")
        for doc in docs:
            staged = await service.find_one_async(req=None, archive_id=doc[ID_FIELD])
            if staged:
                await service.finish_commit(staged)

    async def _pop_staged_upload(self, doc) -> dict | None:
        """Resolve ``staged_id`` into a staged upload and make ``doc`` reference its media.

        Metadata read from the file is used as defaults for fields the client did not send.
        """
        staged_id = doc.pop("staged_id", None)
        if not staged_id:
            return None

        app = get_current_app()
        staged = await get_resource_service("upload_staging").find_one_async(req=None, _id=staged_id)
        if not staged or staged["expires"] <= utcnow():
            abort(404, description=_("Staged upload not found or expired"))
        if str(staged.get("user")) != str(get_user(required=True)[ID_FIELD]):
            abort(403, description=_("Staged upload belongs to another user"))
        if staged.get("status") not in ("ready", "committing"):
            raise SuperdeskApiError.conflictError(
                staged.get("error") or _("Staged upload is not ready to commit"),
                payload={"status": staged.get("status")},
            )

        staged_file = await app.media.get_async(staged["media"])
        if not staged_file:
            abort(404, description=_("Staged upload not found or expired"))

        service = get_resource_service("upload_staging")
        updates = {"expires": utcnow() + timedelta(seconds=app.config["UPLOAD_STAGING_TTL"])}
        if staged["status"] == "ready":
            updates.update(status="committing", archive_id=generate_guid(type=GUID_TAG))
        await service.update_processing(
            {"_id": staged["_id"], "status": staged["status"], "expires": {"$gt": utcnow()}},
            updates,
        )
        staged = await service.find_one_async(req=None, _id=staged["_id"])
        if not staged or staged["status"] != "committing" or staged["expires"] <= utcnow():
            raise SuperdeskApiError.conflictError(_("Staged upload is no longer available"))
        if await get_resource_service("archive").find_one_async(req=None, _id=staged["archive_id"]):
            raise SuperdeskApiError.conflictError(_("Staged upload has already been committed"))
        # Retries and concurrent requests share one MongoDB identity, preventing duplicate items.
        doc[ID_FIELD] = doc["guid"] = staged["archive_id"]

        for key, value in (staged.get("meta") or {}).items():
            doc.setdefault(key, value)

        doc["media"] = staged.get("video_server_id") or staged["media"]
        return staged

    async def _load_staged_binary(self, doc, staged) -> None:
        file = doc.pop("media_fetched")
        stream = TemporaryFile()
        try:
            async with file:
                async for chunk in file:
                    stream.write(chunk)
            stream.seek(0)
        except BaseException:
            stream.close()
            raise
        doc["media"] = FileStorage(
            stream,
            filename=staged.get("filename"),
            content_type=staged["mimetype"],
        )

    async def _set_metadata(self, doc):
        """
        Adds metadata to doc.
        """

        update_dates_for(doc)
        generate_unique_id_and_name(doc)
        doc.setdefault("guid", generate_guid(type=GUID_TAG))
        doc.setdefault(ID_FIELD, doc["guid"])
        doc[VERSION] = 1
        await set_item_expiry({}, doc)

        if not doc.get("_import", None):
            set_original_creator(doc)

        doc.setdefault(ITEM_STATE, CONTENT_STATE.DRAFT)

        if not doc.get("ingest_provider"):
            doc["source"] = get_app_config("DEFAULT_SOURCE_VALUE_FOR_MANUAL_ARTICLES")

        copy_metadata_from_user_preferences(doc)

    async def get_file_from_document(self, doc):
        file = doc.get("media_fetched")
        if file:
            del doc["media_fetched"]
        else:
            content = doc["media"]
            res = process_file_from_stream(content, content_type=content.mimetype)
            file_name, content_type, metadata = res
            logger.debug("Going to save media file with %s " % file_name)
            content.seek(0)
            app = get_current_app()
            with timer("media:put.original"):
                doc["media"] = await app.media.put_async(
                    content, filename=file_name, content_type=content_type, metadata=metadata
                )
            return content, content_type, decode_metadata(metadata)

        return file, file.content_type, file.metadata

    def upload_file_to_video_server(self, doc):
        """
        Upload file to video server and create rendition for it
        :param doc: info of file
        :return:
        """
        # upload video to video server
        res = self.video_editor.create(doc.get("media"))
        doc["media"] = res["_id"]
        metadata = res.get("metadata")
        # create renditions
        rend = {
            "href": res.get("url"),
            "video_editor_id": res.get("_id"),
            "mimetype": res.get("mime_type"),
            "version": res.get("version"),
        }
        renditions = {"original": rend}
        return res, renditions, metadata
