from unittest.mock import AsyncMock, Mock, patch

import superdesk
from superdesk.commands.clean_images import CleanImages
from superdesk.tests import TestCase


class CleanImagesTestCase(TestCase):
    async def test_staged_media_is_referenced(self):
        async def staging_cursor():
            yield {
                "media": "staged-original",
                "renditions": {
                    "thumbnail": {"media": "staged-thumbnail"},
                },
            }
            yield {"media": "another-staged-original"}

        services = {
            "archive": Mock(get_from_mongo=Mock(return_value=[])),
            "archive_versions": Mock(get_from_mongo=Mock(return_value=[])),
            "ingest": Mock(get_from_mongo_async=AsyncMock(return_value=[])),
            "upload": Mock(get_from_mongo_async=AsyncMock(return_value=[])),
            "upload_staging": Mock(get_from_mongo_async=AsyncMock(return_value=staging_cursor())),
        }
        media = Mock()
        app = Mock(media=media)

        with (
            patch.object(superdesk, "get_resource_service", side_effect=services.get),
            patch("superdesk.commands.clean_images.get_app_config", return_value=False),
            patch("superdesk.commands.clean_images.get_current_app", return_value=app),
        ):
            await CleanImages().run()

        services["upload_staging"].get_from_mongo_async.assert_awaited_once_with(req=None, lookup={})
        media.remove_unreferenced_files.assert_called_once_with(
            {"staged-original", "staged-thumbnail", "another-staged-original"}
        )
