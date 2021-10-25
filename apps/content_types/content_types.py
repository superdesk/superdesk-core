import re
import bson
import superdesk

from eve.utils import config
from copy import deepcopy
from superdesk import get_resource_service
from superdesk.errors import SuperdeskApiError
from superdesk.default_schema import DEFAULT_SCHEMA, DEFAULT_EDITOR
from apps.auth import get_user_id
from apps.desks import remove_profile_from_desks
from eve.utils import ParsedRequest
from superdesk.resource import build_custom_hateoas
from flask_babel import _
from superdesk.utc import utcnow


CONTENT_TYPE_PRIVILEGE = "content_type"
DO_NOT_SHOW_SELECTION = "do not show"

# Fields that might not be in the schema but should be still available in formatter/output
REQUIRED_FIELDS = (
    "language",
    "embargoed",
)

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
)


class ContentTypesResource(superdesk.Resource):
    schema = {
        "_id": {
            "type": "string",
            "iunique": True,
        },
        "item_type": {
            "type": "string",
            "nullable": True,
            "content_type_single_item_type": True,
        },
        "label": {
            "type": "string",
            "iunique": True,
        },
        "description": {
            "type": "string",
        },
        "schema": {
            "type": "dict",
            "schema": {},
            "allow_unknown": True,
        },
        "editor": {
            "type": "dict",
            "schema": {},
            "allow_unknown": True,
        },
        "widgets_config": {
            "type": "list",
            "schema": {
                "type": "dict",
                "schema": {"widget_id": {"type": "string"}, "is_displayed": {"type": "boolean"}},
            },
        },
        "priority": {
            "type": "integer",
            "default": 0,
        },
        "enabled": {
            "type": "boolean",
            "default": False,
        },
        "is_used": {
            "type": "boolean",
            "default": False,
        },
        "created_by": superdesk.Resource.rel("users", nullable=True),
        "updated_by": superdesk.Resource.rel("users", nullable=True),
        "init_version": {"type": "integer"},
    }

    item_url = r'regex("[\w,.:-]+")'

    privileges = {"POST": CONTENT_TYPE_PRIVILEGE, "PATCH": CONTENT_TYPE_PRIVILEGE, "DELETE": CONTENT_TYPE_PRIVILEGE}

    datasource = {
        "default_sort": [("priority", -1)],
    }

    mongo_indexes = {
        "label_1": ([("label", 1)], {"unique": True}),
    }


class ContentTypesService(superdesk.Service):
    def _set_updated_by(self, doc):
        doc["updated_by"] = get_user_id()

    def _set_created_by(self, doc):
        doc["created_by"] = get_user_id()

    def on_create(self, docs):
        for doc in docs:
            self._set_updated_by(doc)
            self._set_created_by(doc)

    def on_delete(self, doc):
        if doc.get("is_used"):
            raise SuperdeskApiError(status_code=202, payload={"is_used": True})
        remove_profile_from_templates(doc)
        remove_profile_from_desks(doc)

    def on_update(self, updates, original):
        self._validate_disable(updates, original)
        self._set_updated_by(updates)
        prepare_for_save_content_type(original, updates)
        self._update_template_fields(updates, original)

    def on_delete_res_vocabularies(self, doc):
        req = ParsedRequest()
        req.projection = '{"label": 1}'
        res = self.get(req=req, lookup={"schema." + doc[config.ID_FIELD]: {"$type": 3}})
        if res.count():
            payload = {"content_types": [doc_hateoas for doc_hateoas in map(self._build_hateoas, res)]}
            message = _("Vocabulary {vocabulary} is used in {count} content type(s)").format(
                vocabulary=doc.get("display_name"), count=res.count()
            )
            raise SuperdeskApiError.badRequestError(message, payload)

    def _build_hateoas(self, doc):
        build_custom_hateoas({"self": {"title": "Content Profile", "href": "/content_types/{_id}"}}, doc)
        return doc

    def _validate_disable(self, updates, original):
        """
        Checks the templates and desks that are referencing the given
        content profile if the profile is being disabled
        """
        if "enabled" in updates and updates.get("enabled") is False and original.get("enabled") is True:
            templates = list(
                superdesk.get_resource_service("content_templates").get_templates_by_profile_id(original.get("_id"))
            )

            if len(templates) > 0:
                template_names = ", ".join([t.get("template_name") for t in templates])
                raise SuperdeskApiError.badRequestError(
                    message=_(
                        "Cannot disable content profile as following templates are referencing: {templates}"
                    ).format(templates=template_names)
                )

            req = ParsedRequest()
            all_desks = list(superdesk.get_resource_service("desks").get(req=req, lookup={}))
            profile_desks = [
                desk for desk in all_desks if desk.get("default_content_profile") == str(original.get("_id"))
            ]

            if len(profile_desks) > 0:
                profile_desk_names = ", ".join([d.get("name") for d in profile_desks])
                raise SuperdeskApiError.badRequestError(
                    message=_("Cannot disable content profile as following desks are referencing: {desks}").format(
                        desks=profile_desk_names
                    )
                )

    def _update_template_fields(self, updates, original):
        """
        Finds the templates that are referencing the given
        content profile an clears the disabled fields
        """

        # these are the only fields of templates that don't depend on the schema.
        template_metadata_fields = ["language", "usageterms"]

        templates = list(
            superdesk.get_resource_service("content_templates").get_templates_by_profile_id(original.get("_id"))
        )

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

    def find_one(self, req, **lookup):
        doc = super().find_one(req, **lookup)
        if doc and req and "edit" in req.args:
            prepare_for_edit_content_type(doc)
        if doc:
            clean_doc(doc)
        return doc

    def set_used(self, profile_ids):
        """Set `is_used` flag for content profiles.

        :param profile_ids
        """
        query = {"_id": {"$in": list(profile_ids)}, "is_used": {"$ne": True}}
        update = {"$set": {"is_used": True}}
        self.find_and_modify(query=query, update=update)

    def get_output_name(self, profile):
        try:
            _id = bson.ObjectId(profile)
            item = self.find_one(req=None, _id=_id) or {}
            return re.compile("[^0-9a-zA-Z_]").sub("", item.get("label", str(_id)))
        except bson.errors.InvalidId:
            return profile


def clean_doc(doc):
    schema = doc.get("schema", {})
    editor = doc.get("editor", {})
    vocabularies = get_resource_service("vocabularies").get_forbiden_custom_vocabularies()

    for vocabulary in vocabularies:
        field = vocabulary.get("schema_field", vocabulary["_id"])
        if schema.get(field):
            del schema[field]
        if editor.get(field):
            del editor[field]

    clean_json(schema)
    clean_json(editor)


def clean_json(json):
    if not isinstance(json, dict):
        return
    for key in list(json.keys()):
        value = json[key]
        if value is None:
            del json[key]
        else:
            clean_json(value)


def prepare_for_edit_content_type(doc):
    clean_doc(doc)
    init_default(doc)
    editor = doc["editor"]
    schema = doc["schema"]
    fields_map, field_names = get_fields_map_and_names()
    init_custom(editor, schema, fields_map)
    expand_subject(editor, schema, fields_map)
    set_field_name(editor, field_names)
    init_extra_fields(editor, schema)
    doc["_updated"] = utcnow()


def init_extra_fields(editor, schema):
    fields = get_resource_service("vocabularies").get_extra_fields()
    for field in fields:
        field_type = field.get("field_type")
        schema.setdefault(field["_id"], {"type": field_type, "required": False})
        if field["_id"] in editor:
            editor[field["_id"]]["enabled"] = True
        else:
            editor[field["_id"]] = {"enabled": False}
        editor[field["_id"]]["field_name"] = field["display_name"]


def get_allowed_list(schema):
    try:
        return schema["schema"]["schema"]["scheme"]["allowed"]
    except KeyError:
        return []


def get_mandatory_list(schema):
    return schema["mandatory_in_list"]["scheme"]


def get_fields_map_and_names():
    vocabularies = get_resource_service("vocabularies").get_custom_vocabularies()
    fields_map = {}
    field_names = {}

    for vocabulary in vocabularies:
        if vocabulary.get("selection_type") == DO_NOT_SHOW_SELECTION:
            continue
        fields_map[vocabulary.get("schema_field", vocabulary["_id"])] = vocabulary["_id"]
        field_names[vocabulary["_id"]] = vocabulary.get("display_name", vocabulary["_id"])

    return fields_map, field_names


def init_default(doc):
    editor = doc["editor"] = doc.get("editor", None)
    schema = doc["schema"] = doc.get("schema", None)
    if editor and schema:
        for field in DEFAULT_EDITOR:
            # add missing fields in editor with enabled = false
            if editor.get(field, None) is None:
                editor[field] = deepcopy(DEFAULT_EDITOR[field])
                editor[field]["enabled"] = False
                if schema.get(field, None) is None:
                    schema[field] = deepcopy(DEFAULT_SCHEMA[field])
            else:
                editor[field]["enabled"] = True
    else:
        doc["editor"] = deepcopy(DEFAULT_EDITOR)
        doc["schema"] = deepcopy(DEFAULT_SCHEMA)


def init_custom(editor, schema, fields_map):
    # process custom fields defined on vocabularies
    for old_field, field in fields_map.items():
        if field != old_field:
            if editor.get(field, None):
                editor[field]["enabled"] = True
            # custom storage for field, replace default editor with custom one
            replace_key(editor, old_field, field)
            replace_key(schema, old_field, field)
        else:
            # fields are stored in subject so add new custom editor
            schema[field] = {"type": "list", "required": False, "readonly": False}

            if editor.get(field) and "enabled" in editor[field]:
                editor[field]["enabled"] = editor[field].get("enabled")
            elif editor.get(field):
                editor[field]["enabled"] = True
            else:
                editor[field] = {"enabled": False}


def replace_key(dictionary, oldKey, newKey):
    if dictionary.get(oldKey, None):
        if not dictionary.get(newKey, None):
            dictionary[newKey] = deepcopy(dictionary[oldKey])
        del dictionary[oldKey]
    elif not dictionary.get(newKey, None):
        dictionary[newKey] = {}


def expand_subject(editor, schema, fields_map):
    subject = get_subject_name(fields_map)
    allowed = get_allowed_list(schema[subject])
    mandatory = get_mandatory_list(schema[subject])
    default_values = schema[subject].get("default", [])
    schema[subject]["schema"] = {}
    set_enabled_for_custom(editor, allowed, fields_map)
    set_required_for_custom(editor, schema, mandatory, fields_map)
    set_readonly_for_custom(editor, schema, mandatory, fields_map)
    set_default_for_custom(schema, default_values, fields_map)


def set_enabled_for_custom(editor, allowed, fields_map):
    for field in allowed:
        editor[fields_map.get(field, field)]["enabled"] = True


def set_required_for_custom(editor, schema, mandatory, fields_map):
    # old notation where `value` is string
    for field, value in tuple((k, v) for k, v in mandatory.items() if type(v) == str):
        if field == value or field == "subject":
            try:
                editor[fields_map.get(field, field)]["required"] = value is not None
                schema[fields_map.get(field, field)]["required"] = value is not None
            except KeyError:
                continue
    # new notation where `value` is dict
    for field, value in tuple((k, v) for k, v in mandatory.items() if type(v) == dict):
        if (field is not None and value.get("required", False)) or field == "subject":
            try:
                editor[fields_map.get(field, field)]["required"] = value.get("required", False)
                schema[fields_map.get(field, field)]["required"] = value.get("required", False)
            except KeyError:
                continue


def set_readonly_for_custom(editor, schema, mandatory, fields_map):
    # old notation where `value` is string
    for field, value in tuple((k, v) for k, v in mandatory.items() if type(v) == str):
        try:
            editor[fields_map.get(field, field)]["readonly"] = False
            schema[fields_map.get(field, field)]["readonly"] = False
        except KeyError:
            continue
    # new notation where `value` is dict
    for field, value in tuple((k, v) for k, v in mandatory.items() if type(v) == dict):
        if (field is not None and value.get("readonly", False)) or field == "subject":
            try:
                editor[fields_map.get(field, field)]["readonly"] = value.get("readonly", False)
                schema[fields_map.get(field, field)]["readonly"] = value.get("readonly", False)
            except KeyError:
                continue


def set_default_for_custom(schema, default_values, fields_map):
    for old_field, field in fields_map.items():
        if (field == old_field or old_field == "subject") and schema.get(field, None) is not None:
            default = []
            for value in default_values:
                if value.get("scheme", None) == field:
                    default.append(value)
            schema[field]["default"] = default


def get_subject_name(fields_map):
    return fields_map.get("subject", "subject")


def set_field_name(editor, field_names):
    for (field, name) in field_names.items():
        editor.setdefault(field, {})["field_name"] = name


def prepare_for_save_content_type(original, updates):
    editor = updates["editor"] = updates.get("editor", {})
    schema = updates["schema"] = updates.get("schema", {})
    original = deepcopy(original)
    prepare_for_edit_content_type(original)
    concatenate_dictionary(original["editor"], editor)
    concatenate_dictionary(original["schema"], schema)
    delete_disabled_fields(editor, schema)
    fields_map, _ = get_fields_map_and_names()
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


def concatenate_dictionary(source, destination):
    for key in source:
        if key not in destination:
            destination[key] = source[key]


def delete_disabled_fields(editor, schema):
    for field, value in editor.items():
        if value is None or not value.get("enabled", False):
            editor[field] = None
            schema[field] = None


def clean_editor(editor):
    for field_value in editor.values():
        if not field_value:
            continue
        for attribute in list(field_value.keys()):
            if attribute not in EDITOR_ATTRIBUTES:
                del field_value[attribute]


def compose_subject_schema(schema, fields_map):
    mandatory = {}
    allowed = []
    default = []
    for old_field, field in fields_map.items():
        if (old_field == field or old_field == "subject") and schema.get(field, None):
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
            if schema[field].get("default", None):
                default.extend(schema[field]["default"])
        else:
            mandatory[old_field] = None
    if allowed:
        init_subject_schema(schema, default, mandatory, allowed, fields_map)


def init_subject_schema(schema, default, mandatory, allowed, fields_map):
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


def init_editor_required(editor, schema):
    for field in schema:
        if editor.get(field) and schema.get(field) and schema[field].get("required") is not None:
            schema[field]["nullable"] = not schema[field]["required"]


def init_schema_for_custom_fields(schema, fields_map):
    for field in fields_map.values():
        if schema.get(field, None) and schema[field].get("default", None):
            list_values = schema[field]["default"]
            for value in list_values:
                value["scheme"] = field


def rename_schema_for_custom_fields(schema, fields_map):
    for old_field, field in fields_map.items():
        if field in schema:
            if old_field != field:
                schema[old_field] = schema[field]
            del schema[field]


def is_enabled(field, schema):
    """Return true if field is enabled using given schema.

    :param field: field name
    :param schema: schema dict
    """
    return schema.get(field) or schema.get(field) == {} or field not in DEFAULT_SCHEMA or field in REQUIRED_FIELDS


def apply_schema(item):
    """Return item without fields that should not be there given it's profile.

    :param item: item to apply schema to
    """
    # fields that can be added to article without being added to CP eg: using widgets
    allowed_keys = ["attachments", "refs", "place", "organisation", "person"]

    if item.get("type") == "event":
        return item.copy()
    try:
        profile = get_resource_service("content_types").find_one(req=None, _id=item["profile"])
        schema = profile["schema"]
    except Exception:
        schema = DEFAULT_SCHEMA
    return {key: val for key, val in item.items() if is_enabled(key, schema) or key in allowed_keys}


def remove_profile_from_templates(item):
    """Removes the profile data from templates that are using the profile

    :param item: deleted content profile
    """
    templates = list(
        superdesk.get_resource_service("content_templates").get_templates_by_profile_id(item.get(config.ID_FIELD))
    )
    for template in templates:
        template.get("data", {}).pop("profile", None)
        superdesk.get_resource_service("content_templates").patch(template[config.ID_FIELD], template)
