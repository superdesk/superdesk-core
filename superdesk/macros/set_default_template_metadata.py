import logging
from flask import current_app as app
from flask_babel import lazy_gettext
from superdesk import get_resource_service

logger = logging.getLogger(__name__)


def get_default_content_template(item, **kwargs):
    if "dest_desk_id" in kwargs:
        desk = None
        desk_id = kwargs["dest_desk_id"]
    elif "desk" in kwargs:
        desk = kwargs["desk"]
        desk_id = kwargs["desk"]["_id"]
    elif "task" in item and "desk" in item["task"]:
        desk = None
        desk_id = item["task"].get("desk")
    else:
        logger.warning("Can't set default data, no desk identifier found")
        return

    if desk is None:
        desk = get_resource_service("desks").find_one(req=None, _id=desk_id)
    if not desk:
        logger.warning('Can\'t find desk with id "{desk_id}"'.format(desk_id=desk_id))
        return

    content_template_id = desk.get("default_content_template")
    if not content_template_id:
        logger.warning("No default content template set for {desk_name}".format(desk_name=desk.get("name", desk_id)))
        return
    content_template = get_resource_service("content_templates").find_one(req=None, _id=content_template_id)
    if not content_template:
        logger.warning(
            'Can\'t find content_template with id "{content_template_id}"'.format(
                content_template_id=content_template_id
            )
        )
        return

    return content_template


def set_default_template_metadata(item, **kwargs):

    fields_to_exclude = app.config.get("DEFAULT_TEMPLATE_METADATA_MACRO_EXCLUDE", {})
    fields_to_override = app.config.get("DEFAULT_TEMPLATE_METADATA_MACRO_OVERRIDE", {})

    """Replace some metadata from default content template"""

    content_template = get_default_content_template(item, **kwargs)
    if not content_template:
        return

    data = content_template["data"]

    vocabularies = get_resource_service("vocabularies").get(req=None, lookup={"field_type": {"$exists": True}})
    for vocabulary in vocabularies:
        fields_to_exclude.append(vocabulary["_id"])

    for key, value in data.items():
        if (not item.get(key) and key not in fields_to_exclude) or key in fields_to_override:
            item[key] = data.get(key)

    # subject contains remaining metadata to copy
    subject = data.setdefault("subject", [])

    # we first take out the metadata which we want to add, if any
    to_add = []
    for sub in subject:
        if sub.get("scheme") and not any(
            subjects.get("scheme") == sub.get("scheme") for subjects in item.get("subject", [])
        ):
            to_add.append(sub)

    # and now we add the new one
    item.setdefault("subject", []).extend([i for i in to_add if i.get("scheme") and to_add])

    if not item["subject"] and data.get("subject"):
        item["subject"] = data.get("subject")

    return item


name = "Set Default Template Metadata"
label = lazy_gettext("Set Default Template Metadata")
callback = set_default_template_metadata
access_type = "backend"
action_type = "direct"
