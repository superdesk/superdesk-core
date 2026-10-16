from io import BytesIO
from tempfile import NamedTemporaryFile
from unittest.mock import AsyncMock, patch
import os
import asyncio

from bson import ObjectId
from werkzeug.datastructures import FileStorage
from werkzeug.exceptions import Conflict

import superdesk
from apps.archive.archive_media import ArchiveMediaService
from apps.archive.upload_staging import process_staged_upload, expire_staged_uploads
from superdesk.celery_app.task_result import AsyncTaskResult
from superdesk.errors import SuperdeskApiError
from superdesk.media.renditions import create_renditions_for_file
from superdesk.media.metadata import read_metadata
from superdesk.core.types import SuperdeskAsyncFile
from superdesk.tests import TestCase, setup_auth_user
from superdesk.utc import utcnow
from datetime import timedelta
from tests import fixture_path


class UploadStagingTestCase(TestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.service = superdesk.get_resource_service("upload_staging")
        self.user = {"_id": ObjectId(), "byline": "Test User"}
        self.user_patch = patch("apps.archive.upload_staging.get_user", return_value=self.user)
        self.user_patch.start()
        self.addCleanup(self.user_patch.stop)
        with open(fixture_path("cp.jpg", "media"), "rb") as source:
            self.binary = source.read()

    async def stage(self):
        doc = {"media": FileStorage(BytesIO(self.binary), filename="cp.jpg", content_type="image/jpeg")}
        await self.service.on_create_async([doc])
        await self.service.create_async([doc])
        return doc

    async def test_dispatch_does_not_read_a_task_result(self):
        staged = await self.stage()
        with (
            patch("apps.archive.upload_staging.process_staged_upload.delay", new_callable=AsyncMock) as dispatch,
            patch.object(AsyncTaskResult, "get_result_async", side_effect=AssertionError("result backend used")),
        ):
            await self.service.on_created_async([staged])
        dispatch.assert_awaited_once_with(staged["_id"])
        self.assertEqual(staged["status"], "pending")
        self.assertNotIn("renditions", staged)

    async def test_confirmation_rejects_media_replacement(self):
        staged = await self.stage()
        for replacement in (
            FileStorage(BytesIO(b"replacement"), filename="replacement.jpg", content_type="image/jpeg"),
            staged["media"],
            None,
        ):
            with self.subTest(media=replacement):
                with self.assertRaises(SuperdeskApiError) as error:
                    await self.service.on_update_async({"confirmed": True, "media": replacement}, staged)
                self.assertEqual(error.exception.status_code, 400)
        current = await self.service.find_one_async(None, _id=staged["_id"])
        self.assertEqual(current["media"], staged["media"])
        self.assertIsNotNone(await self.app.media.get_async(staged["media"]))

    async def test_confirmation_without_media_remains_allowed(self):
        staged = await self.stage()
        await self.service.on_update_async({"confirmed": True}, staged)

    async def test_worker_updates_invalidate_conditional_gets(self):
        self.headers = []
        await setup_auth_user(self)
        with patch("apps.archive.upload_staging.process_staged_upload.delay", new_callable=AsyncMock):
            response = await self.client.post(
                "/api/upload_staging",
                headers=self.headers,
                files={"media": FileStorage(BytesIO(self.binary), filename="cp.jpg", content_type="image/jpeg")},
            )
        self.assertEqual(response.status_code, 201)
        staged = await response.get_json()
        url = f"/api/upload_staging/{staged['_id']}"
        response = await self.client.get(url, headers=self.headers)
        initial = await response.get_json()
        initial_etag = response.headers["ETag"]
        initial_modified = response.headers["Last-Modified"]
        cached = await self.client.get(url, headers=[*self.headers, ("If-None-Match", initial_etag)])
        self.assertEqual(cached.status_code, 304)
        metadata_snapshot = {}

        async def generate(*args, **kwargs):
            response = await self.client.get(url, headers=[*self.headers, ("If-None-Match", initial_etag)])
            self.assertEqual(response.status_code, 200)
            metadata = await response.get_json()
            self.assertNotEqual(metadata["_etag"], initial["_etag"])
            self.assertGreater(metadata["_updated"], initial["_updated"])
            self.assertEqual(metadata["metadata_status"], "ready")
            self.assertIn("Montreal Police", metadata["meta"]["description_text"])
            metadata_snapshot.update(metadata)
            metadata_snapshot["http_etag"] = response.headers["ETag"]
            response = await self.client.get(url, headers=[*self.headers, ("If-Modified-Since", initial_modified)])
            self.assertEqual(response.status_code, 200)
            return await create_renditions_for_file(*args, **kwargs)

        async def transition(query, updates):
            nonlocal clock
            clock += timedelta(seconds=1)
            return await update_processing(query, updates)

        clock = utcnow()
        update_processing = self.service.update_processing
        with (
            patch("apps.archive.upload_staging.utcnow", side_effect=lambda **kwargs: clock),
            patch.object(self.service, "update_processing", side_effect=transition),
            patch("apps.archive.upload_staging.create_renditions_for_file", side_effect=generate),
        ):
            await process_staged_upload.run(staged["_id"])
        response = await self.client.get(
            url, headers=[*self.headers, ("If-None-Match", metadata_snapshot["http_etag"])]
        )
        self.assertEqual(response.status_code, 200)
        ready = await response.get_json()
        self.assertNotEqual(ready["_etag"], metadata_snapshot["_etag"])
        self.assertGreater(ready["_updated"], metadata_snapshot["_updated"])
        self.assertEqual(ready["status"], "ready")
        self.assertIn("viewImage", ready["renditions"])
        response = await self.client.get(url, headers=[*self.headers, ("If-None-Match", response.headers["ETag"])])
        self.assertEqual(response.status_code, 304)

    async def test_processing_update_retries_after_concurrent_confirmation(self):
        staged = await self.stage()
        atomic_update = self.service.find_and_modify_async
        attempts = 0

        async def confirm_then_update(query, update):
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                await self.service.update_async(
                    staged["_id"], {"confirmed": True, "_etag": "concurrent-confirmation"}, staged
                )
            return await atomic_update(query, update)

        with patch.object(self.service, "find_and_modify_async", side_effect=confirm_then_update):
            matched = await self.service.update_processing(
                {"_id": staged["_id"], "status": "pending"}, {"status": "processing"}
            )
        self.assertEqual(attempts, 2)
        self.assertTrue(matched["confirmed"])
        current = await self.service.find_one_async(None, _id=staged["_id"])
        self.assertTrue(current["confirmed"])
        self.assertEqual(current["status"], "processing")
        self.assertNotEqual(current["_etag"], "concurrent-confirmation")

    async def test_staging_does_not_parse_metadata_or_read_entire_binary(self):
        class BoundedUpload(BytesIO):
            def read(self, size=-1):
                if size < 0:
                    raise AssertionError("unbounded binary read during staging")
                return super().read(size)

        doc = {"media": FileStorage(BoundedUpload(self.binary), filename="cp.jpg", content_type="image/jpeg")}
        with (
            patch("apps.archive.upload_staging.read_metadata") as embedded,
            patch("apps.archive.upload_staging.process_file") as technical,
        ):
            await self.service.on_create_async([doc])
        embedded.assert_not_called()
        technical.assert_not_called()
        self.assertEqual(doc["metadata_status"], "pending")
        self.assertEqual(doc["size"], len(self.binary))

    async def test_worker_parses_disk_file_and_notifies_after_persisting_metadata(self):
        staged = await self.stage()
        paths = []
        snapshots = []

        def parse_file(path, content_type):
            self.assertIsInstance(path, str)
            self.assertTrue(os.path.isfile(path))
            paths.append(path)
            return read_metadata(path, content_type)

        def notify(name, **kwargs):
            snapshots.append(kwargs)

        with (
            patch("apps.archive.upload_staging.read_metadata", side_effect=parse_file),
            patch("apps.archive.upload_staging.push_notification", side_effect=notify),
            patch.object(SuperdeskAsyncFile, "to_bytes", side_effect=AssertionError("full binary read")),
        ):
            await process_staged_upload.run(staged["_id"])
        self.assertEqual(len(paths), 1)
        self.assertFalse(os.path.exists(paths[0]))
        ready = await self.service.find_one_async(None, _id=staged["_id"])
        self.assertEqual(ready["metadata_status"], "ready")
        self.assertIn("Montreal Police", ready["meta"]["description_text"])
        self.assertEqual(len(snapshots), 2)
        for event in snapshots:
            self.assertEqual(event, {"staged_id": str(staged["_id"]), "user": str(self.user["_id"])})

    async def test_metadata_failure_does_not_prevent_renditions(self):
        staged = await self.stage()
        with patch("apps.archive.upload_staging.read_metadata", side_effect=ValueError("invalid embedded metadata")):
            await process_staged_upload.run(staged["_id"])
        ready = await self.service.find_one_async(None, _id=staged["_id"])
        self.assertEqual(ready["status"], "ready")
        self.assertEqual(ready["metadata_status"], "failed")
        self.assertIn("Enter metadata manually", ready["metadata_error"])
        self.assertIn("viewImage", ready["renditions"])

    async def test_picture_reuses_download_and_publishes_metadata_before_renditions(self):
        staged = await self.stage()
        streams = []
        notifications = []

        def notify(name, **kwargs):
            notifications.append(name)

        async def generate(*args, **kwargs):
            content = kwargs["original_content"]
            self.assertFalse(content.closed)
            streams.append(content)
            current = await self.service.find_one_async(None, _id=staged["_id"])
            self.assertEqual(current["metadata_status"], "ready")
            self.assertEqual(current["status"], "processing")
            self.assertIn("Montreal Police", current["meta"]["description_text"])
            self.assertEqual(notifications, ["upload_staging:updated"])
            return await create_renditions_for_file(*args, **kwargs)

        with (
            patch.object(self.app.media, "get_async", wraps=self.app.media.get_async) as download,
            patch("apps.archive.upload_staging.create_renditions_for_file", side_effect=generate),
            patch("apps.archive.upload_staging.push_notification", side_effect=notify),
            patch.object(SuperdeskAsyncFile, "to_buffer_sync", side_effect=AssertionError("second download")),
        ):
            await process_staged_upload.run(staged["_id"])
        download.assert_awaited_once_with(staged["media"])
        self.assertTrue(streams[0].closed)
        self.assertEqual(notifications, ["upload_staging:updated", "upload_staging:updated"])
        ready = await self.service.find_one_async(None, _id=staged["_id"])
        self.assertEqual(ready["status"], "ready")
        self.assertIn("viewImage", ready["renditions"])

    async def test_worker_persists_renditions_without_dispatching_another_task(self):
        staged = await self.stage()
        with (
            patch("superdesk.media.renditions.create_renditions_in_celery_task.delay") as dispatch,
            patch.object(AsyncTaskResult, "get_result_async", side_effect=AssertionError("result backend used")),
        ):
            await process_staged_upload.run(staged["_id"])
        dispatch.assert_not_called()
        result = await self.service.find_one_async(None, _id=staged["_id"])
        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["renditions"]["original"]["media"], staged["media"])
        self.assertIn("viewImage", result["renditions"])
        self.assertTrue(process_staged_upload.ignore_result)
        self.assertFalse(process_staged_upload.store_async_result)

    async def test_pending_commit_is_rejected_without_waiting(self):
        staged = await self.stage()
        with patch("apps.archive.archive_media.get_user", return_value=self.user):
            with self.assertRaises(SuperdeskApiError) as error:
                await ArchiveMediaService()._pop_staged_upload({"staged_id": staged["_id"]})
        self.assertEqual(error.exception.status_code, 409)

    async def test_duplicate_worker_delivery_does_not_regenerate_renditions(self):
        staged = await self.stage()
        await process_staged_upload.run(staged["_id"])
        with patch("apps.archive.upload_staging.create_renditions_for_file") as generate:
            await process_staged_upload.run(staged["_id"])
        generate.assert_not_called()

    async def test_commit_reuses_worker_output(self):
        staged = await self.stage()
        await process_staged_upload.run(staged["_id"])
        staged = await self.service.find_one_async(None, _id=staged["_id"])
        doc = {"staged_id": staged["_id"], "headline": "Edited"}
        with (
            patch("apps.archive.archive_media.get_user", return_value=self.user),
            patch("apps.archive.archive_media.create_renditions_in_celery") as dispatch,
            patch.object(ArchiveMediaService, "_set_metadata", new_callable=AsyncMock),
            patch("apps.archive.archive_media.add_activity", new_callable=AsyncMock),
        ):
            await ArchiveMediaService().on_create_async([doc])
        dispatch.assert_not_called()
        self.assertEqual(doc["renditions"], staged["renditions"])
        self.assertEqual(doc["headline"], "Edited")
        claimed = await self.service.find_one_async(None, _id=staged["_id"])
        self.assertEqual(claimed["status"], "committing")
        await superdesk.get_resource_service("archive").create_async([doc])
        await ArchiveMediaService().on_created_async([doc])
        self.assertIsNone(await self.service.find_one_async(None, _id=staged["_id"]))
        self.assertIsNotNone(await self.app.media.get_async(staged["media"]))

    async def test_commit_merges_missing_extra_defaults_without_overwriting_explicit_values(self):
        self.app.config["PICTURE_METADATA_MAPPING"] = {
            "extra.filename": "Description",
            "extra.credit": "Creator",
        }
        staged = await self.stage()
        await process_staged_upload.run(staged["_id"])
        ready = await self.service.find_one_async(None, _id=staged["_id"])
        defaults = ready["meta"]["extra"]
        self.assertTrue(defaults["filename"])
        self.assertTrue(defaults["credit"])

        for supplied in ({}, {"unrelated": "Custom"}, {"filename": "Edited"}, {"filename": ""}, {"filename": None}):
            with self.subTest(extra=supplied):
                doc = {"staged_id": staged["_id"], "extra": supplied.copy(), "headline": ""}
                with patch("apps.archive.archive_media.get_user", return_value=self.user):
                    await ArchiveMediaService()._pop_staged_upload(doc)
                self.assertEqual(doc["extra"], {**defaults, **supplied})
                self.assertEqual(doc["headline"], "")
                current = await self.service.find_one_async(None, _id=staged["_id"])
                self.assertEqual(current["meta"]["extra"], defaults)

        doc = {"staged_id": staged["_id"]}
        with patch("apps.archive.archive_media.get_user", return_value=self.user):
            await ArchiveMediaService()._pop_staged_upload(doc)
        self.assertEqual(doc["extra"], defaults)

    async def test_failed_archive_insert_can_retry_without_losing_staging(self):
        staged = await self.stage()
        await process_staged_upload.run(staged["_id"])
        archive = superdesk.get_resource_service("archive")
        with (
            patch("apps.archive.archive_media.get_user", return_value=self.user),
            patch("apps.archive.archive_media.add_activity", new_callable=AsyncMock),
        ):
            first = {"staged_id": staged["_id"]}
            await ArchiveMediaService().on_create_async([first])
            with patch.object(archive.backend, "create_async", side_effect=RuntimeError("database unavailable")):
                with self.assertRaisesRegex(RuntimeError, "database unavailable"):
                    await archive.create_async([first])
            retry = {"staged_id": staged["_id"], "headline": "Retried"}
            await ArchiveMediaService().on_create_async([retry])
            self.assertEqual(retry["_id"], first["_id"])
            self.assertFalse(await self.service.discard(staged["_id"]))
            await archive.create_async([retry])
            await ArchiveMediaService().on_created_async([retry])
        self.assertIsNone(await self.service.find_one_async(None, _id=staged["_id"]))
        self.assertIsNotNone(await self.app.media.get_async(staged["media"]))

    async def test_archive_validation_failure_keeps_staging_for_retry(self):
        staged = await self.stage()
        await process_staged_upload.run(staged["_id"])
        archive = superdesk.get_resource_service("archive")
        with (
            patch("apps.archive.archive_media.get_user", return_value=self.user),
            patch("apps.archive.archive_media.add_activity", new_callable=AsyncMock),
        ):
            first = {"staged_id": staged["_id"]}
            with patch.object(
                archive, "_test_readonly_stage", side_effect=SuperdeskApiError.badRequestError("Invalid desk")
            ):
                with self.assertRaises(SuperdeskApiError):
                    await archive.on_create_async([first])
            claimed = await self.service.find_one_async(None, _id=staged["_id"])
            self.assertEqual(claimed["status"], "committing")
            retry = {"staged_id": staged["_id"]}
            await ArchiveMediaService().on_create_async([retry])
            self.assertEqual(retry["_id"], first["_id"])
            await archive.create_async([retry])
            await ArchiveMediaService().on_created_async([retry])
        self.assertIsNone(await self.service.find_one_async(None, _id=staged["_id"]))

    async def test_expiry_preserves_committed_media_if_finalization_was_interrupted(self):
        staged = await self.stage()
        await process_staged_upload.run(staged["_id"])
        with (
            patch("apps.archive.archive_media.get_user", return_value=self.user),
            patch("apps.archive.archive_media.add_activity", new_callable=AsyncMock),
        ):
            doc = {"staged_id": staged["_id"]}
            await ArchiveMediaService().on_create_async([doc])
        await superdesk.get_resource_service("archive").create_async([doc])
        claimed = await self.service.find_one_async(None, _id=staged["_id"])
        await self.service.update_async(staged["_id"], {"expires": utcnow() - timedelta(seconds=1)}, claimed)
        await expire_staged_uploads.run()
        self.assertIsNone(await self.service.find_one_async(None, _id=staged["_id"]))
        for rendition in doc["renditions"].values():
            self.assertIsNotNone(await self.app.media.get_async(rendition["media"]))

    async def test_overlapping_commits_share_one_archive_identity(self):
        staged = await self.stage()
        await process_staged_upload.run(staged["_id"])
        first = {"staged_id": staged["_id"]}
        second = {"staged_id": staged["_id"]}
        with (
            patch("apps.archive.archive_media.get_user", return_value=self.user),
            patch("apps.archive.archive_media.add_activity", new_callable=AsyncMock),
        ):
            await ArchiveMediaService().on_create_async([first])
            await ArchiveMediaService().on_create_async([second])
        self.assertEqual(first["_id"], second["_id"])
        archive = superdesk.get_resource_service("archive")
        await archive.create_async([first])
        with self.assertRaises(Conflict):
            await archive.create_async([second])
        await ArchiveMediaService().on_created_async([first])
        self.assertIsNone(await self.service.find_one_async(None, _id=staged["_id"]))
        self.assertIsNotNone(await self.app.media.get_async(staged["media"]))

    async def test_expiry_cleans_unpersisted_commit(self):
        staged = await self.stage()
        await process_staged_upload.run(staged["_id"])
        with (
            patch("apps.archive.archive_media.get_user", return_value=self.user),
            patch("apps.archive.archive_media.add_activity", new_callable=AsyncMock),
        ):
            await ArchiveMediaService().on_create_async([{"staged_id": staged["_id"]}])
        claimed = await self.service.find_one_async(None, _id=staged["_id"])
        await self.service.update_async(staged["_id"], {"expires": utcnow() - timedelta(seconds=1)}, claimed)
        await expire_staged_uploads.run()
        self.assertIsNone(await self.service.find_one_async(None, _id=staged["_id"]))
        for rendition in claimed["renditions"].values():
            self.assertIsNone(await self.app.media.get_async(rendition["media"]))

    async def test_failure_is_recorded_in_mongo(self):
        staged = await self.stage()
        with patch("apps.archive.upload_staging.create_renditions_for_file", side_effect=ValueError("invalid image")):
            with self.assertRaisesRegex(ValueError, "invalid image"):
                await process_staged_upload.run(staged["_id"])
        result = await self.service.find_one_async(None, _id=staged["_id"])
        self.assertEqual(result["status"], "failed")
        self.assertIn("Media processing failed", result["error"])

    async def test_cancellation_during_download_records_failure_and_notifies(self):
        staged = await self.stage()
        downloading = asyncio.Event()
        paths = []

        def temporary_file(*args, **kwargs):
            file = NamedTemporaryFile(*args, **kwargs)
            paths.append(file.name)
            return file

        async def download_chunk():
            downloading.set()
            await asyncio.Future()

        with (
            patch.object(SuperdeskAsyncFile, "__anext__", side_effect=download_chunk),
            patch("apps.archive.upload_staging.NamedTemporaryFile", side_effect=temporary_file),
            patch("apps.archive.upload_staging.delete_staged_media", new_callable=AsyncMock) as cleanup,
            patch("apps.archive.upload_staging.push_notification") as notify,
        ):
            worker = asyncio.create_task(process_staged_upload.run(staged["_id"]))
            await asyncio.wait_for(downloading.wait(), timeout=5)
            worker.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await worker
        current = await self.service.find_one_async(None, _id=staged["_id"])
        self.assertEqual(current["status"], "failed")
        self.assertIn("Media processing failed", current["error"])
        cleanup.assert_awaited_once()
        self.assertFalse(cleanup.call_args.kwargs["original"])
        notify.assert_called_once_with(
            "upload_staging:updated", staged_id=str(staged["_id"]), user=str(self.user["_id"])
        )
        self.assertEqual(len(paths), 1)
        self.assertFalse(os.path.exists(paths[0]))

    async def test_discard_removes_original_and_renditions(self):
        staged = await self.stage()
        await process_staged_upload.run(staged["_id"])
        result = await self.service.find_one_async(None, _id=staged["_id"])
        await self.service.discard(staged["_id"])
        for rendition in result["renditions"].values():
            self.assertIsNone(await self.app.media.get_async(rendition["media"]))

    async def test_discard_during_processing_cleans_worker_output(self):
        staged = await self.stage()
        generated = {}

        async def generate_then_discard(*args, **kwargs):
            generated.update(await create_renditions_for_file(*args, **kwargs))
            await self.service.discard(staged["_id"])
            await self.service.delete_async({"_id": staged["_id"]})
            return generated

        with patch("apps.archive.upload_staging.create_renditions_for_file", side_effect=generate_then_discard):
            await process_staged_upload.run(staged["_id"])
        self.assertIsNone(await self.service.find_one_async(None, _id=staged["_id"]))
        for rendition in generated.values():
            self.assertIsNone(await self.app.media.get_async(rendition["media"]))

    async def test_expiry_removes_media_and_document(self):
        staged = await self.stage()
        await process_staged_upload.run(staged["_id"])
        ready = await self.service.find_one_async(None, _id=staged["_id"])
        await self.service.update_async(staged["_id"], {"expires": utcnow() - timedelta(seconds=1)}, ready)
        await expire_staged_uploads.run()
        self.assertIsNone(await self.service.find_one_async(None, _id=staged["_id"]))
        for rendition in ready["renditions"].values():
            self.assertIsNone(await self.app.media.get_async(rendition["media"]))

    async def test_video_server_processing_is_done_by_worker_and_reused_on_commit(self):
        self.app.config["VIDEO_SERVER_ENABLED"] = True
        staged = await self.stage()
        await self.service.update_async(staged["_id"], {"mimetype": "video/mp4"}, staged)
        renditions = {"original": {"video_editor_id": "video-id", "href": "https://video.example/original"}}
        with (
            patch.object(
                ArchiveMediaService,
                "upload_file_to_video_server",
                return_value=({"_id": "video-id"}, renditions, {"duration": 5}),
            ) as upload_video,
            patch.object(ArchiveMediaService.video_editor, "create_timeline_thumbnails") as thumbnails,
        ):
            await process_staged_upload.run(staged["_id"])
            ready = await self.service.find_one_async(None, _id=staged["_id"])
            self.assertEqual(ready["status"], "awaiting_confirmation")
            upload_video.assert_not_called()
            await self.service.update_async(staged["_id"], {"confirmed": True}, ready)
            await process_staged_upload.run(staged["_id"], renditions_only=True)
            ready = await self.service.find_one_async(None, _id=staged["_id"])
            self.assertEqual(ready["status"], "ready")
            self.assertEqual(ready["video_server_id"], "video-id")
            doc = {"staged_id": staged["_id"]}
            with (
                patch("apps.archive.archive_media.get_user", return_value=self.user),
                patch.object(ArchiveMediaService, "_set_metadata", new_callable=AsyncMock),
                patch("apps.archive.archive_media.add_activity", new_callable=AsyncMock),
            ):
                await ArchiveMediaService().on_create_async([doc])
            self.assertIsNotNone(await self.app.media.get_async(staged["media"]))
            await superdesk.get_resource_service("archive").create_async([doc])
            await ArchiveMediaService().on_created_async([doc])
        upload_video.assert_called_once()
        thumbnails.assert_called_once()
        self.assertEqual(doc["media"], "video-id")
        self.assertEqual(doc["renditions"], renditions)
        self.assertIsNone(await self.app.media.get_async(staged["media"]))

    async def test_video_metadata_aliases_are_defaults_on_commit_without_changing_raw_metadata(self):
        staged = await self.stage()
        await self.service.update_async(staged["_id"], {"mimetype": "video/mp4"}, staged)
        raw = {"Rights": "Embedded copyright", "Credit": "Embedded credit"}
        with patch("apps.archive.upload_staging.read_metadata", return_value=raw):
            await process_staged_upload.run(staged["_id"])
        current = await self.service.find_one_async(None, _id=staged["_id"])
        self.assertEqual(current["raw_metadata"], raw)
        self.assertEqual(current["meta"]["copyrightnotice"], "Embedded copyright")
        self.assertEqual(current["meta"]["creditline"], "Embedded credit")
        await self.service.update_async(staged["_id"], {"confirmed": True}, current)
        await process_staged_upload.run(staged["_id"], renditions_only=True)
        doc = {"staged_id": staged["_id"], "creditline": "Edited credit"}
        with patch("apps.archive.archive_media.get_user", return_value=self.user):
            await ArchiveMediaService()._pop_staged_upload(doc)
        self.assertEqual(doc["copyrightnotice"], "Embedded copyright")
        self.assertEqual(doc["creditline"], "Edited credit")
        self.assertEqual(raw, {"Rights": "Embedded copyright", "Credit": "Embedded credit"})

    async def test_video_metadata_aliases_preserve_canonical_and_configured_mapping_values(self):
        self.app.config["PICTURE_METADATA_MAPPING"] = {"extra.original_credit": "Credit"}
        staged = await self.stage()
        await self.service.update_async(staged["_id"], {"mimetype": "video/mp4"}, staged)
        raw = {
            "Rights": "Video copyright",
            "Credit": "Video credit",
            "CopyrightNotice": "Canonical copyright",
            "CreditLine": "Canonical credit",
        }
        with patch("apps.archive.upload_staging.read_metadata", return_value=raw):
            await process_staged_upload.run(staged["_id"])
        current = await self.service.find_one_async(None, _id=staged["_id"])
        self.assertEqual(current["raw_metadata"], raw)
        self.assertEqual(current["meta"]["copyrightnotice"], "Canonical copyright")
        self.assertEqual(current["meta"]["creditline"], "Canonical credit")
        self.assertEqual(current["meta"]["extra"]["original_credit"], "Video credit")
