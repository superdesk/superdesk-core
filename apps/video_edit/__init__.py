from flask_babel import _

import superdesk
from apps.archive.common import ARCHIVE
from superdesk import config
from superdesk.errors import SuperdeskApiError
from superdesk.media.video_editor import VideoEditorWrapper
from superdesk.metadata.utils import item_url


TIMELINE_THUMBNAILS_AMOUNT = 60


class VideoEditService(superdesk.Service):
    """
    Use video server for editing video.
    """

    video_editor = VideoEditorWrapper()

    def create(self, docs, **kwargs):
        ids = []
        for doc in docs:
            item = doc.get("item")
            item_id = item[config.ID_FIELD]
            renditions = item["renditions"]
            video_id = renditions["original"].get("video_editor_id")
            if not video_id:
                raise SuperdeskApiError.badRequestError(message=_('"video_editor_id" is required'))
            if "capture" not in doc and "edit" not in doc:
                raise SuperdeskApiError.badRequestError(message=_('"capture" or "edit" is required'))

            # push task capture preview thumbnail to video server
            if "capture" in doc:
                capture = doc.pop("capture")
                project = self.video_editor.capture_preview_thumbnail(
                    video_id, position=capture.get("position"), crop=capture.get("crop"), rotate=capture.get("rotate")
                )
                renditions.setdefault("viewImage", {}).update(
                    {
                        "href": project["thumbnails"]["preview"].get("url"),
                        "mimetype": project["thumbnails"]["preview"].get("mime_type", "image/png"),
                    }
                )

                # clean up old thumbnails
                renditions.pop("baseImage", None)
                renditions.pop("thumbnail", None)
            # push task edit video to video server
            if "edit" in doc:
                edit = doc.pop("edit")
                project = self.video_editor.edit(video_id, edit)
                renditions.setdefault("original", {}).update(
                    {
                        "href": project["url"],
                        "mimetype": project.get("mime_type", "video/mp4"),
                        "version": project["version"] + 1,
                        "video_editor_id": project.get("_id"),
                    }
                )

            original_item = super().find_one(req=None, _id=item_id)
            updates = self.system_update(id=item_id, updates={"renditions": renditions}, original=original_item)
            item.update(updates)
            ids.append(item_id)
        return ids

    def find_one(self, req, **lookup):
        res = super().find_one(req, **lookup)
        if req is None:
            return res

        video_id = res["renditions"]["original"]["video_editor_id"]
        if req.args.get("action") == "timeline":
            response = self.video_editor.create_timeline_thumbnails(
                video_id, req.args.get("amount", TIMELINE_THUMBNAILS_AMOUNT)
            )
            return {config.ID_FIELD: video_id, **response}
        res["project"] = self.video_editor.find_one(video_id)
        return res

    def on_replace(self, document, original):
        """
        Override to upload thumbnails
        """
        if not document.get("file"):
            return
        # avoid dump file storage
        file = document.pop("file")
        project = original.pop("project")
        data = self.video_editor.upload_preview_thumbnail(project.get("_id"), file)
        document.update(original)
        renditions = document.get("renditions", {})
        renditions.setdefault("viewImage", {}).update(
            {
                "href": data.get("url"),
                "mimetype": data.get("mimetype"),
            }
        )
        renditions.pop("baseImage", None)
        renditions.pop("thumbnail", None)
        document.update({"renditions": renditions})
        return document


class VideoEditResource(superdesk.Resource):
    item_methods = ["GET", "PUT"]
    resource_methods = ["POST"]
    privileges = {
        "POST": ARCHIVE,
        "PUT": ARCHIVE,
    }
    datasource = {
        "projection": {
            "processing": 1,
            "thumbnails": 1,
            "project": 1,
            "renditions": 1,
        }
    }
    item_url = item_url
    schema = {
        "file": {"type": "file"},
        "item": {
            "type": "dict",
            "required": False,
            "empty": True,
            "schema": {
                config.ID_FIELD: {
                    "type": "string",
                    "required": True,
                },
                "renditions": {
                    "type": "dict",
                    "required": True,
                    "allow_unknown": True,
                    "schema": {"original": {"type": "dict", "required": True, "empty": False}},
                },
            },
        },
        "edit": {
            "type": "dict",
            "required": False,
            "empty": False,
            "schema": {
                "trim": {
                    "required": False,
                    "regex": "^\\d+\\.?\\d*,\\d+\\.?\\d*$",
                },
                "rotate": {"type": "integer", "required": False, "allowed": [-270, -180, -90, 90, 180, 270]},
                "scale": {"type": "integer", "required": False},
                "crop": {"required": False, "regex": "^\\d+,\\d+,\\d+,\\d+$"},
            },
        },
        "capture": {
            "type": "dict",
            "required": False,
            "empty": False,
            "schema": {
                "position": {
                    "required": False,
                    "type": "float",
                },
                "rotate": {"type": "integer", "required": False, "allowed": [-270, -180, -90, 90, 180, 270]},
                "scale": {"type": "integer", "required": False},
                "crop": {"required": False, "regex": "^\\d+,\\d+,\\d+,\\d+$"},
            },
        },
    }


def init_app(app):
    video_edit_service = VideoEditService(ARCHIVE, backend=superdesk.get_backend())
    VideoEditResource("video_edit", app=app, service=video_edit_service)
