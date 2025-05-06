import superdesk
from superdesk.metadata.item import CONTENT_TYPE, CONTENT_STATE, get_schema

from superdesk.core import get_current_app
from superdesk.eve_async import AsyncBaseService
from superdesk.resource_fields import (
    ID_FIELD,
    DATE_CREATED,
    LAST_UPDATED,
    ETAG,
    VERSION,
    ITEM_STATE,
    ITEM_TYPE,
)
from superdesk.flask import render_template, render_template_string, abort
from superdesk.errors import SuperdeskApiError
from .service import get_highlight_name
from apps.archive.common import ITEM_EXPORT_HIGHLIGHT, ITEM_CREATE_HIGHLIGHT

PACKAGE_FIELDS = {
    "type",
    "state",
    "groups",
    "unique_name",
    "pubstatus",
    "origina_creator",
    "flags",
    "guid",
    "schedule_settings",
    "expiry",
    "format",
    "lock_time",
    "lock_user",
    "lock_session",
    ID_FIELD,
    LAST_UPDATED,
    DATE_CREATED,
    ETAG,
    "version",
    "_current_version",
    "version_creator",
    "operation",
    "unique_id",
    "version_created",
    "fields_meta",
}


async def get_template(highlight_id):
    """Return the string template associated with highlightId or none"""
    if not highlight_id:
        return None
    highlight_service = superdesk.get_resource_service("highlights")
    highlight = await highlight_service.find_one_async(req=None, _id=highlight_id)
    if not highlight or not highlight.get("template"):
        return None

    template_service = superdesk.get_resource_service("content_templates")
    template = await template_service.find_one_async(req=None, _id=highlight.get("template"))
    return template


class GenerateHighlightsService(AsyncBaseService):
    async def create_async(self, docs, **kwargs):
        """Generate highlights text item for given package.

        If doc.preview is True it won't save the item, only return.
        """
        service = superdesk.get_resource_service("archive")
        app = get_current_app().as_any()
        preview = False
        for doc in docs:
            preview = doc.get("preview", False)
            package = await service.find_one_async(req=None, _id=doc["package"])
            if not package:
                abort(404)
            export = doc.get("export")
            template = await get_template(package.get("highlight"))
            string_template = None
            if template and template.get("data") and template["data"].get("body_html"):
                string_template = template["data"]["body_html"]

            doc.clear()
            doc[ITEM_TYPE] = CONTENT_TYPE.TEXT
            doc["family_id"] = package.get("guid")
            doc[ITEM_STATE] = CONTENT_STATE.SUBMITTED
            doc[VERSION] = 1

            for field in package:
                if field not in PACKAGE_FIELDS:
                    doc[field] = package[field]

            items = []
            for group in package.get("groups", []):
                for ref in group.get("refs", []):
                    if "residRef" in ref:
                        item = await service.find_one_async(req=None, _id=ref.get("residRef"))
                        if item:
                            if not (export or preview) and (
                                item.get("lock_session") or item.get("state") != "published"
                            ):
                                message = "Locked or not published items in highlight list."
                                raise SuperdeskApiError.forbiddenError(message)

                            items.append(item)
                            if not preview:
                                await app.on_archive_item_updated.call_async(
                                    {
                                        "highlight_id": package.get("highlight"),
                                        "highlight_name": await get_highlight_name(package.get("highlight")),
                                    },
                                    item,
                                    ITEM_EXPORT_HIGHLIGHT,
                                )

            if string_template:
                doc["body_html"] = await render_template_string(string_template, package=package, items=items)
            else:
                doc["body_html"] = await render_template("default_highlight_template.txt", package=package, items=items)
        if preview:
            return ["" for doc in docs]
        else:
            ids = await service.post_async(docs, **kwargs)
            for item_id in ids:
                await app.on_archive_item_updated.call_async(
                    {
                        "highlight_id": package.get("highlight"),
                        "highlight_name": await get_highlight_name(package.get("highlight")),
                    },
                    {"_id": item_id},
                    ITEM_CREATE_HIGHLIGHT,
                )
            return ids


class GenerateHighlightsResource(superdesk.Resource):
    """Generate highlights item for given package."""

    schema = {
        "package": {
            # not setting relation here, we will fetch it anyhow
            "type": "string",
            "required": True,
        },
        "preview": {
            "type": "boolean",
            "default": False,
        },
        "export": {
            "type": "boolean",
            "default": False,
        },
        "type": {
            "type": "string",
            "readonly": True,
        },
    }
    schema.update(get_schema(versioning=True))

    resource_methods = ["POST"]
    item_methods = []
    privileges = {"POST": "highlights"}
