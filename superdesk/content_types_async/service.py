# This file is TODO-ASYNC of Superdesk.
#
# Copyright 2013, 2025 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


from copy import deepcopy
from typing import Any, cast

import bson
from bson import ObjectId
from quart_babel import gettext as _

from apps.auth import get_user_id
from apps.desks import remove_profile_from_desks_async
from apps.templates.content_templates import ContentTemplatesService
import superdesk
from superdesk.core.resources.service import AsyncCacheableService
from superdesk.core.types.search import ProjectedFieldArg, SearchRequest
from superdesk.default_schema import DEFAULT_EDITOR, DEFAULT_SCHEMA, DEFAULT_SCHEMA_MAP
from superdesk.errors import SuperdeskApiError
from superdesk.resource_fields import ID_FIELD
from superdesk.types.content_types import ContentTypesResourceModel
from superdesk.types.desks import DesksResourceModel
from superdesk.utc import utcnow
from superdesk.utils import format_content_type_name
from superdesk.vocabularies_async.service import VocabulariesService
from superdesk.flask import request


CONTENT_TYPE_PRIVILEGE = "content_type"
DO_NOT_SHOW_SELECTION = "do not show"

# Fields that might not be in the schema but should be still available in formatter/output
REQUIRED_FIELDS = ("language", "embargoed")

# Valid editor keys
EDITOR_ATTRIBUTES = (
    "order",
    "sdWidth",
    "required",
    "readonly",
    "hideDate",
    "showCrops",
    "formatOptions",
    "editor3",
    "default",
    "cleanPastedHTML",
    "imageTitle",
    "sourceField",
    "section",
    "preview",
    "enabled",
    "field_name",
    "allow_toggling",
)

# cvs hardcoded in the app wich special use
# and not supposed to be added to content profile
HARDCODED_CVS = ("languages",)


class ContentTypesService(AsyncCacheableService[ContentTypesResourceModel]):
    resource_name = "content_types"

    async def on_create(self, docs: list[ContentTypesResourceModel]) -> None:
        for doc in docs:
            doc.created_by = doc.updated_by = get_user_id()

    async def on_delete(self, doc: ContentTypesResourceModel) -> None:
        if doc.is_used:
            raise SuperdeskApiError(status_code=202, payload={"is_used": True})
        await remove_profile_from_templates(doc)
        await remove_profile_from_desks_async(doc.to_dict())

    async def on_update(self, updates: dict[str, Any], original: ContentTypesResourceModel) -> None:
        await self._validate_disable(updates, original)
        updates["updated_by"] = get_user_id()
        await prepare_for_save_content_type(original, updates)
        await self._update_template_fields(updates, original)

    async def on_delete_res_vocabularies(self, doc: dict[str, Any]) -> None:
        cursor = await self.find({"schema." + doc[ID_FIELD]: {"$type": 3}}, projection=["label"])
        if count := await cursor.count():
            message = _("Vocabulary {vocabulary} is used in {count} content type(s)").format(
                vocabulary=doc.get("display_name"), count=count
            )
            raise SuperdeskApiError.badRequestError(message)

    async def _validate_disable(self, updates: dict[str, Any], original: ContentTypesResourceModel) -> None:
        """
        checks the templates and desks that are referencing the given
        content profile if the profile is being disabled
        """
        if (enabled := updates.get("enabled")) is not None and not enabled and original.enabled:
            # TODO-ASYNC: "content_templates" is not async yet
            content_templates_service = superdesk.get_resource_service("content_templates")
            assert content_templates_service is not None
            content_templates_service = cast(ContentTemplatesService, content_templates_service)
            templates = list(content_templates_service.get_templates_by_profile_id(original.id))

            if len(templates) > 0:
                template_names = ", ".join([t.get("template_name") for t in templates])
                raise SuperdeskApiError.badRequestError(
                    message=_(
                        "Cannot disable content profile as following templates are referencing: {templates}"
                    ).format(templates=template_names)
                )

            all_desks = [desk async for desk in DesksResourceModel.get_service().get_all()]
            profile_desks = [desk for desk in all_desks if desk.default_content_profile == str(original.id)]

            if len(profile_desks) > 0:
                profile_desk_names = ", ".join([d.name for d in profile_desks])
                raise SuperdeskApiError.badRequestError(
                    message=_("Cannot disable content profile as following desks are referencing: {desks}").format(
                        desks=profile_desk_names
                    )
                )

    async def _update_template_fields(self, updates: dict[str, Any], original: ContentTypesResourceModel) -> None:
        """
        Finds the templates that are referencing the given
        content profile an clears the disabled fields
        """
        # these are the only fields of templates that don't depend on the schema.
        template_metadata_fields = ["usageterms"]

        # TODO-ASYNC: "content_templates" is not async yet
        content_templates_service = superdesk.get_resource_service("content_templates")
        assert content_templates_service is not None
        content_templates_service = cast(ContentTemplatesService, content_templates_service)
        templates = list(content_templates_service.get_templates_by_profile_id(original.id))

        for template in templates:
            data = deepcopy(template.get("data", {}))
            schema = updates.get("schema", {})
            processed = False
            for field, params in schema.items():
                if (not params or not params.get("enabled", True)) and field not in template_metadata_fields:
                    data.pop(field, None)
                    processed = True
            if processed:
                superdesk.get_resource_service("content_templates").patch(template.get("_id"), {"data": data})

    async def find_by_id_raw(
        self,
        item_id: str | ObjectId,
        version: int | None = None,
        projection: ProjectedFieldArg | None = None,
    ) -> dict | None:
        doc_dict = await super().find_by_id_raw(item_id, version, projection)
        if not doc_dict:
            return None

        doc = ContentTypesResourceModel.from_dict(doc_dict)
        if request and request.args.get("edit"):
            await prepare_for_edit_content_type(doc)
        else:
            await clean_doc(doc)
        return doc.to_dict()

    async def set_used(self, profile_ids: list[str]) -> None:
        query = {"_id": {"$in": list(profile_ids)}, "is_used": {"$ne": True}}
        update = {"$set": {"is_used": True}}
        await self.mongo_async.find_and_modify(query=query, update=update)

    async def get_output_name(self, profile: str) -> str:
        try:
            _id = ObjectId(profile)
            item = await self.find_by_id(_id)
            return format_content_type_name(item.to_dict() if item else {}, str(_id))
        except bson.errors.InvalidId:
            return profile

    async def get_schema(self, item: dict[str, Any]) -> dict[str, Any] | None:
        profile_id = item.get("profile") or item.get("type")
        if profile_id is None:
            raise ValueError("No profile_id found.")
        profile = await self.find_by_id(profile_id)
        if profile:
            return profile.content_schema
        return DEFAULT_SCHEMA_MAP.get(profile_id)


async def clean_doc(doc: ContentTypesResourceModel) -> None:
    schema = doc.content_schema
    editor = doc.editor

    vocabularies_service = VocabulariesService()

    vocabularies = list(voc.to_dict() for voc in await vocabularies_service.get_forbiden_custom_vocabularies())

    for cv in HARDCODED_CVS:
        vocabularies.append({"_id": cv})

    for vocabulary in vocabularies:
        field = vocabulary.get("schema_field", vocabulary["_id"])
        if schema.get(field):
            del schema[field]
        if editor.get(field):
            del editor[field]


def clean_null(doc: ContentTypesResourceModel) -> None:
    for field in ("editor", "content_schema"):
        data = getattr(doc, field)
        to_delete = [key for key, val in data.items() if val is None]
        for key in to_delete:
            del data[key]


async def prepare_for_edit_content_type(doc: ContentTypesResourceModel) -> None:
    await clean_doc(doc)
    init_default(doc)
    editor = doc.editor
    schema = doc.content_schema
    fields_map, field_names = await get_fields_map_and_names()
    init_custom(editor, schema, fields_map)
    expand_subject(editor, schema, fields_map)
    set_field_name(editor, field_names)
    await init_extra_fields(editor, schema)
    clean_null(doc)
    doc.updated = utcnow()


async def init_extra_fields(editor: dict[str, Any], schema: dict[str, Any]) -> None:
    vocabularies_service = VocabulariesService()
    fields = await vocabularies_service.get_extra_fields()
    for field in fields:
        field_type = field.field_type
        if schema.get(str(field.id)) is None:
            schema[str(field.id)] = {"type": field_type, "required": False}
        if editor.get(str(field.id)):
            editor[str(field.id)].setdefault("enabled", True)
        else:
            editor[str(field.id)] = {"enabled": False}
        editor[str(field.id)]["field_name"] = field.display_name


def get_allowed_list(schema: dict[str, Any]) -> list:
    try:
        return schema["schema"]["schema"]["scheme"]["allowed"]
    except KeyError:
        return []


def get_mandatory_list(schema: dict[str, Any]) -> dict:
    return schema["mandatory_in_list"]["scheme"]


async def get_fields_map_and_names() -> tuple[dict[str, str], dict[str, str]]:
    vocabularies_service = VocabulariesService()
    vocabularies = await vocabularies_service.get_custom_vocabularies()
    fields_map = {}
    field_names = {}

    for vocabulary in vocabularies:
        if vocabulary.selection_type == DO_NOT_SHOW_SELECTION:
            continue
        if str(vocabulary.id) in DEFAULT_SCHEMA and not vocabulary.schema_field:
            continue
        if str(vocabulary.id) in HARDCODED_CVS:
            continue
        fields_map[vocabulary.schema_field or str(vocabulary.id)] = str(vocabulary.id)
        field_names[str(vocabulary.id)] = vocabulary.display_name or str(vocabulary.id)

    return fields_map, field_names


def init_default(doc: ContentTypesResourceModel) -> None:
    editor = doc.editor
    schema = doc.content_schema
    if editor and schema:
        for field in DEFAULT_EDITOR:
            # add missing fields in editor with enabled = false
            if editor.get(field, None) is None:
                editor[field] = deepcopy(DEFAULT_EDITOR[field])
                editor[field]["enabled"] = False
            else:  # it's there, so why change it?
                editor[field].setdefault("enabled", True)
            if schema.get(field, None) is None:
                schema[field] = deepcopy(DEFAULT_SCHEMA[field])
    else:
        doc.editor = deepcopy(DEFAULT_EDITOR)
        doc.content_schema = deepcopy(DEFAULT_SCHEMA)


def init_custom(editor: dict[str, Any], schema: dict[str, Any], fields_map: dict[str, str]) -> None:
    # process custom fields defined on vocabularies
    for old_field, field in fields_map.items():
        if field != old_field:
            if editor.get(field, None):
                editor[field]["enabled"] = True
            # custom storage for field, replace default editor with custom one
            replace_key(editor, old_field, field)
            replace_key(schema, old_field, field)
        else:
            # we add the custom cv field in schema so we can change it's schema
            # attributes, but we should probably find a different model which
            # would not require this so we don't have any conflicts with core fields
            schema[field] = {"type": "list", "required": False, "readonly": False}
            # fields are stored in subject so add new custom editor
            if editor.get(field) and "enabled" in editor[field]:
                editor[field]["enabled"] = editor[field].get("enabled")
            elif editor.get(field):
                editor[field]["enabled"] = True
            else:
                editor[field] = {"enabled": False}


def replace_key(dictionary: dict[str, Any], oldKey: str, newKey: str) -> None:
    if dictionary.get(oldKey, None):
        if not dictionary.get(newKey, None):
            dictionary[newKey] = deepcopy(dictionary[oldKey])
        del dictionary[oldKey]
    elif not dictionary.get(newKey, None):
        dictionary[newKey] = {}


def expand_subject(editor: dict[str, Any], schema: dict[str, Any], fields_map: dict[str, str]) -> None:
    subject = get_subject_name(fields_map)
    allowed = get_allowed_list(schema[subject])
    mandatory = get_mandatory_list(schema[subject])
    default_values = schema[subject].get("default", [])
    schema[subject]["schema"] = {}
    set_enabled_for_custom(editor, allowed, fields_map)
    set_required_for_custom(editor, schema, mandatory, fields_map)
    set_readonly_for_custom(editor, schema, mandatory, fields_map)
    set_default_for_custom(schema, default_values, fields_map)


def set_enabled_for_custom(editor: dict[str, Any], allowed: list[str], fields_map: dict[str, str]) -> None:
    for field in allowed:
        try:
            editor[fields_map.get(field, field)]["enabled"] = True
        except KeyError:
            pass


def set_required_for_custom(
    editor: dict[str, Any], schema: dict[str, Any], mandatory: dict[str, Any], fields_map: dict[str, str]
) -> None:
    # old notation where `value` is string
    for field, value in tuple((k, v) for k, v in mandatory.items() if isinstance(v, str)):
        if field == value or field == "subject":
            try:
                editor[fields_map.get(field, field)]["required"] = value is not None
                schema[fields_map.get(field, field)]["required"] = value is not None
            except KeyError:
                continue
    # new notation where `value` is dict
    for field, value in mandatory.items():
        if isinstance(value, dict):
            if (field is not None and value.get("required", False)) or field == "subject":
                try:
                    key = fields_map.get(field, field)
                    required_flag = value.get("required", False)
                    editor[key]["required"] = required_flag
                    schema[key]["required"] = required_flag
                except KeyError:
                    continue


def set_readonly_for_custom(
    editor: dict[str, Any], schema: dict[str, Any], mandatory: dict[str, Any], fields_map: dict[str, str]
) -> None:
    # new notation where `value` is dict
    for field, value in tuple((k, v) for k, v in mandatory.items() if isinstance(v, str)):
        try:
            editor[fields_map.get(field, field)]["readonly"] = False
            schema[fields_map.get(field, field)]["readonly"] = False
        except KeyError:
            continue
    # new notation where `value` is dict
    for field, value in mandatory.items():
        if isinstance(value, dict):
            if (field is not None and value.get("readonly", False)) or field == "subject":
                try:
                    key = fields_map.get(field, field)
                    readonly_flag = value.get("readonly", False)
                    editor[key]["readonly"] = readonly_flag
                    schema[key]["readonly"] = readonly_flag
                except KeyError:
                    continue


def set_default_for_custom(
    schema: dict[str, Any], default_values: list[dict[str, Any]], fields_map: dict[str, str]
) -> None:
    for old_field, field in fields_map.items():
        if (field == old_field or old_field == "subject") and schema.get(field, None) is not None:
            default = []
            for value in default_values:
                if value.get("scheme", None) == field:
                    default.append(value)
            schema[field]["default"] = default


def get_subject_name(fields_map: dict[str, str]) -> str:
    return fields_map.get("subject", "subject")


def set_field_name(editor: dict[str, Any], field_names: dict[str, str]) -> None:
    for field, name in field_names.items():
        try:
            editor.setdefault(field, {})["field_name"] = name
        except TypeError:
            pass


async def prepare_for_save_content_type(original: ContentTypesResourceModel, updates: dict[str, Any]) -> None:
    editor = updates.setdefault("editor", {})
    schema = updates.setdefault("schema", {})
    original = deepcopy(original)
    await prepare_for_edit_content_type(original)
    concatenate_dictionary(original.editor, editor)
    concatenate_dictionary(original.content_schema, schema)
    delete_disabled_fields(editor, schema)
    fields_map, _ = await get_fields_map_and_names()
    clean_editor(editor)
    init_schema_for_custom_fields(schema, fields_map)
    compose_subject_schema(schema, fields_map)
    if not editor.get("subject"):
        # subject must not be mandatory if not present in editor
        # Note that it can still be used for custom vocabularies
        try:
            schema["subject"]["required"] = False
        except (TypeError, KeyError):
            pass
    init_editor_required(editor, schema)
    rename_schema_for_custom_fields(schema, fields_map)


def concatenate_dictionary(source: dict[str, Any], destination: dict[str, Any]) -> None:
    for key in source:
        if key not in destination:
            destination[key] = source[key]


def delete_disabled_fields(editor: dict[str, Any], schema: dict[str, Any]) -> None:
    for field, value in editor.items():
        if value is None or not value.get("enabled", False):
            editor[field] = None
            schema[field] = None


def clean_editor(editor: dict[str, Any]) -> None:
    for field_value in editor.values():
        if not field_value:
            continue
        for attribute in list(field_value.keys()):
            if attribute not in EDITOR_ATTRIBUTES:
                del field_value[attribute]


def compose_subject_schema(schema: dict[str, Any], fields_map: dict[str, str]) -> None:
    mandatory: dict[str, Any] = {}
    allowed = []
    default = []
    for old_field, field in fields_map.items():
        if (old_field == field or old_field == "subject") and schema.get(field):
            allowed.append(field)
            if schema[field].get("required", False) and schema[field].get("readonly", False):
                mandatory[old_field] = {
                    "required": True,
                    "readonly": True,
                }
            elif schema[field].get("required", False):
                mandatory[old_field] = {
                    "required": True,
                    "readonly": False,
                }
            elif schema[field].get("readonly", False):
                mandatory[old_field] = {
                    "required": False,
                    "readonly": True,
                }
            else:
                mandatory[old_field] = None
            if schema[field].get("default"):
                default.extend(schema[field]["default"])
        else:
            mandatory[old_field] = None
    if allowed:
        init_subject_schema(schema, default, mandatory, allowed, fields_map)


def init_subject_schema(
    schema: dict[str, Any],
    default: list[dict[str, Any]],
    mandatory: dict[str, Any],
    allowed: list[str],
    fields_map: dict[str, str],
) -> None:
    subject = get_subject_name(fields_map)
    try:
        is_required = schema["subject"]["required"]
        is_readonly = schema["subject"].get("readonly", False)
    except (KeyError, TypeError):
        is_required = DEFAULT_SCHEMA["subject"].get("required", False)
        is_readonly = DEFAULT_SCHEMA["subject"].get("readonly", False)
    schema[subject] = deepcopy(DEFAULT_SCHEMA["subject"])
    schema[subject]["default"] = default
    schema[subject]["mandatory_in_list"]["scheme"] = mandatory
    schema[subject]["schema"]["schema"]["scheme"]["allowed"] = allowed
    if "subject" in mandatory:  # custom subject field
        schema[subject]["required"] = mandatory.get("subject") is not None
    else:
        schema[subject]["required"] = is_required
        schema[subject]["readonly"] = is_readonly


def init_editor_required(editor: dict[str, Any], schema: dict[str, Any]) -> None:
    for field in schema:
        if editor.get(field) and schema.get(field) and schema[field].get("required") is not None:
            schema[field]["nullable"] = not schema[field]["required"]


def init_schema_for_custom_fields(schema: dict[str, Any], fields_map: dict[str, str]) -> None:
    for field in fields_map.values():
        if schema.get(field, None) and schema[field].get("default", None):
            list_values = schema[field]["default"]
            for value in list_values:
                value["scheme"] = field


def rename_schema_for_custom_fields(schema: dict[str, Any], fields_map: dict[str, str]) -> None:
    for old_field, field in fields_map.items():
        if field in schema:
            if old_field != field:
                schema[old_field] = schema[field]
            del schema[field]


def is_enabled(field: str, schema: dict[str, Any]) -> bool:
    """Return true if field is enabled using given schema.

    :param field: field name
    :param schema: schema dict
    """
    return schema.get(field) or schema.get(field) == {} or field not in DEFAULT_SCHEMA or field in REQUIRED_FIELDS


async def apply_schema(item: dict[str, Any]) -> dict[str, Any]:
    """Return item without fields that should not be there given it's profile.

    :param item: item to apply schema to
    """
    # fields that can be added to article without being added to CP eg: using widgets
    allowed_keys = ["attachments", "refs", "place", "organisation", "person", "authors"]

    if item.get("type") == "event":
        return item.copy()

    schema = DEFAULT_SCHEMA
    if item.get("profile"):
        profile = await get_profile(item["profile"])
        if profile:
            assert isinstance(profile, ContentTypesResourceModel)
            if profile.content_schema:
                schema = profile.content_schema

    return {key: val for key, val in item.items() if is_enabled(key, schema) or key in allowed_keys}


async def remove_profile_from_templates(item: ContentTypesResourceModel) -> None:
    """Removes the profile data from templates that are using the profile

    :param item: deleted content profile
    """
    # TODO-ASYNC: "content_templates" is not async yet
    templates = list(superdesk.get_resource_service("content_templates").get_templates_by_profile_id(item.id))
    for template in templates:
        template.get("data", {}).pop("profile", None)
        superdesk.get_resource_service("content_templates").patch(template[ID_FIELD], template)


async def get_profile(_id: str) -> dict[str, Any] | ContentTypesResourceModel | None:
    content_types_service = ContentTypesService()
    return await content_types_service.get_cached_by_id(_id)
