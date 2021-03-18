import os
from typing import Optional, Dict, Any
import superdesk
from superdesk.logging import logger

from flask import current_app, request
from werkzeug.utils import secure_filename
from apps.auth import get_user_id


RESOURCE = "attachments"


class AttachmentsResource(superdesk.Resource):
    schema = {
        "media": {"type": "media"},
        "mimetype": {"type": "string"},
        "filename": {"type": "string"},
        "length": {"type": "integer"},
        "title": {
            "type": "string",
            "required": True,
            "sams": {"field": "name"},
        },
        "description": {"type": "string"},
        "user": superdesk.Resource.rel("users"),
        "internal": {
            "type": "boolean",
            "default": False,
            "sams": {"field": "state", "map_value": {False: "public", True: "internal"}},
        },
    }

    item_methods = ["GET", "PATCH"]
    resource_methods = ["GET", "POST"]
    privileges = {"POST": "archive", "PATCH": "archive"}


class AttachmentsService(superdesk.Service):
    def on_create(self, docs):
        for doc in docs:
            doc["user"] = get_user_id()

            # If a `media` argument is passed into the request url then use that as the id for the media item
            # This is so that SAMS client can manually create this link between SAMS and the article
            if request.args.get("media"):
                doc["media"] = request.args["media"]

            if doc.get("media"):
                media = current_app.media.get(doc["media"], RESOURCE)
                doc.setdefault("filename", secure_filename(os.path.basename(getattr(media, "filename"))))
                doc.setdefault("mimetype", getattr(media, "content_type"))
                doc.setdefault("length", getattr(media, "length"))

    def on_deleted(self, doc):
        current_app.media.delete(doc["media"], RESOURCE)


def is_attachment_public(attachment):
    """Retuns true if attachment is public. False if it's internal.

    :param attachment: Attachment object or id inside attachment attribute
    :return: boolean
    """
    if attachment.get("attachment"):  # retrieve object reference
        attachment = superdesk.get_resource_service("attachments").find_one(req=None, _id=attachment["attachment"])

    return not attachment.get("internal")


def get_attachment_public_url(attachment: Dict[str, Any]) -> Optional[str]:
    """Returns the file url for the attachment provided

    :param dict attachment: The attachment to get the file URL
    :rtype: str
    :return: None if the attachment is not public, otherwise the public URL to the file
    """

    if attachment.get("attachment"):  # retrieve object reference
        attachment = superdesk.get_resource_service("attachments").find_one(req=None, _id=attachment["attachment"])

    if attachment.get("internal"):
        return None

    if not attachment.get("media"):
        # All attachments should have a `media` attribute set
        # The provided attachment dict must be invalid
        attachment_id = str(attachment.get("_id"))
        logger.warn(f'Attachment "{attachment_id}" has no media attribute set')

        return None

    return current_app.media.url_for_external(attachment["media"], RESOURCE)


def init_app(app) -> None:
    superdesk.register_resource(RESOURCE, AttachmentsResource, AttachmentsService)
    app.client_config["attachments_max_files"] = app.config.get("ATTACHMENTS_MAX_FILES", 10)
    app.client_config["attachments_max_size"] = app.config.get("ATTACHMENTS_MAX_SIZE", 2 ** 20 * 8)  # 8MB
