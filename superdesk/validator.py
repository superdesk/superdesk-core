# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import re
import superdesk

from bson import ObjectId
from bson.errors import InvalidId
from cerberus import errors
from eve.io.mongo import Validator
from eve.utils import config
from eve.auth import auth_field_and_value
from flask import current_app as app
from flask_babel import _
from eve.validation import SingleErrorAsStringErrorHandler
from werkzeug.datastructures import FileStorage


ERROR_PATTERN = "pattern"
ERROR_UNIQUE = "unique"
ERROR_MINLENGTH = "minlength"
ERROR_REQUIRED = "required"
ERROR_JSON_LIST = "json_list"

CLIENT_ERRORS = (
    ERROR_UNIQUE,
    ERROR_PATTERN,
    ERROR_REQUIRED,
    ERROR_MINLENGTH,
    ERROR_JSON_LIST,
)


class BaseErrorHandler(SingleErrorAsStringErrorHandler):
    def _unpack_single_element_lists(self, tree):
        for field in tree:
            error_list = tree[field]
            if len(error_list) > 0 and isinstance(tree[field][-1], dict):
                self._unpack_single_element_lists(tree[field][-1])
                # if there are sub field errors only return these for now
                if len(error_list) and any([isinstance(err, dict) for err in error_list]):
                    _errors = {}
                    for err in error_list:
                        if isinstance(err, dict):
                            _errors.update(err)
                    tree[field] = _errors
            if len(tree[field]) == 1 and isinstance(tree[field], list):
                tree[field] = tree[field][0]


class SuperdeskErrorHandler(BaseErrorHandler):
    def _format_message(self, field, error):
        if error.info and error.info[0] in CLIENT_ERRORS:
            return {error.info[0]: [1]}  # value must be list, will be unpacked
        elif error.code == errors.REQUIRED_FIELD.code:
            return {ERROR_REQUIRED: [1]}
        return self.messages[error.code].format(
            *error.info, constraint=error.constraint, field=field, value=error.value
        )


class SuperdeskValidator(Validator):
    def __init__(self, *args, **kwargs):
        kwargs["error_handler"] = SuperdeskErrorHandler
        super(SuperdeskValidator, self).__init__(*args, **kwargs)

    def _validate_mapping(self, mapping, field, value):
        """
        {'type': 'dict', 'nullable': True}
        """
        pass

    def _validate_index(self, definition, field, value):
        """
        {'type': 'string'}
        """
        pass

    def _validate_type_phone_number(self, value):
        """Enables validation for `phone_number` schema attribute.

        :param field: field name.
        :param value: field value.
        """
        if re.match("^(?:(?:0?[1-9][0-9]{8})|(?:(?:\+|00)[1-9][0-9]{9,11}))$", value):
            return True

    def _validate_type_email(self, value):
        """Enables validation for `email` schema attribute.

        :param field: field name.
        :param value: field value.
        """
        # it's tricky to write proper regex for email validation, so we
        # should use simple one, or use libraries like
        # - https://pypi.python.org/pypi/email_validator
        # - https://pypi.python.org/pypi/pyIsEmail
        # given that admins are usually create users, not users by themself,
        # probably just check for @ is enough
        # https://davidcel.is/posts/stop-validating-email-addresses-with-regex/
        if re.match(".+@.+", value, re.IGNORECASE):
            return True

    def _validate_type_file(self, value):
        """Enables validation for `file` schema attribute."""
        if isinstance(value, FileStorage):
            return True

    def _validate_multiple_emails(self, multiple, field, value):
        """
        {'type': 'boolean'}
        """
        if multiple:
            emails = value.split(",")
            if not all([self._validate_type_email(email) for email in emails]):
                self._error(field, ERROR_PATTERN)

    def _validate_unique(self, unique, field, value):
        """
        {'type': 'boolean'}
        """
        if not self.resource.endswith("autosave") and unique:
            query = {field: value}
            self._set_id_query(query)
            conflict = superdesk.get_resource_service(self.resource).find_one(req=None, **query)
            if conflict:
                self._error(field, ERROR_UNIQUE)

    def _set_id_query(self, query):
        if self.document_id:
            try:
                query[config.ID_FIELD] = {"$ne": ObjectId(self.document_id)}
            except InvalidId:
                query[config.ID_FIELD] = {"$ne": self.document_id}

    def _validate_iunique(self, unique, field, value):
        """
        {'type': 'boolean'}
        """
        if unique:
            pattern = "^{}$".format(re.escape(value.strip()))
            query = {field: re.compile(pattern, re.IGNORECASE)}
            self._set_id_query(query)
            cursor = superdesk.get_resource_service(self.resource).get_from_mongo(req=None, lookup=query)
            if cursor.count():
                self._error(field, ERROR_UNIQUE)

    def _validate_iunique_per_parent(self, parent_field, field, value):
        """
        {'type': 'string'}
        """
        original = self.persisted_document or {}
        update = self.document or {}

        parent_field_value = update.get(parent_field, original.get(parent_field))

        if parent_field:
            pattern = "^{}$".format(re.escape(value.strip()))
            query = {field: re.compile(pattern, re.IGNORECASE), parent_field: parent_field_value}
            self._set_id_query(query)

            cursor = superdesk.get_resource_service(self.resource).get_from_mongo(req=None, lookup=query)
            if cursor.count():
                self._error(field, ERROR_UNIQUE)

    def _validate_minlength(self, min_length, field, value):
        """
        {'type': 'integer'}
        """
        if isinstance(value, (type(""), list)):
            if len(value) < min_length:
                self._error(field, ERROR_MINLENGTH)

    def _validate_required_fields(self, document):
        """
        {'type': 'list'}
        """
        required = list(field for field, definition in self.schema.items() if definition.get("required") is True)
        missing = set(required) - set(
            key for key in document.keys() if document.get(key) is not None or not self.ignore_none_values
        )
        for field in missing:
            self._error(field, ERROR_REQUIRED)

    def _validate_type_json_list(self, field, value):
        """It will fail later when loading."""
        if not isinstance(value, type("")):
            self._error(field, ERROR_JSON_LIST)

    def _validate_unique_to_user(self, unique, field, value):
        """
        {'type': 'boolean'}
        """
        doc = getattr(self, "document", getattr(self, "original_document", {}))

        if "user" in doc:
            _, auth_value = auth_field_and_value(self.resource)
            query = {"user": auth_value}
        else:
            query = {"user": {"$exists": False}}

        self._is_value_unique(unique, field, value, query)

    def _validate_unique_template(self, unique, field, value):
        """
        {'type': 'boolean'}
        """
        original = self.persisted_document or {}
        update = self.document or {}

        is_public = update.get("is_public", original.get("is_public", None))
        template_name = update.get("template_name", original.get("template_name", None))

        if is_public:
            query = {"is_public": True}
        else:
            _, auth_value = auth_field_and_value(self.resource)
            query = {"user": auth_value, "is_public": False}

        query["template_name"] = re.compile("^{}$".format(re.escape(template_name.strip())), re.IGNORECASE)

        if self.document_id:
            id_field = config.DOMAIN[self.resource]["id_field"]
            query[id_field] = {"$ne": self.document_id}

        if superdesk.get_resource_service(self.resource).find_one(req=None, **query):
            self._error(field, "Template Name is not unique")

    def _validate_twitter(self, twitter, field, value):
        """
        {'type': 'boolean'}
        """
        if twitter and value and not re.match("^@[A-Za-z0-9_]{1,15}$", value, re.IGNORECASE):
            self._error(field, ERROR_PATTERN)

    def _validate_username_pattern(self, enabled, field, value):
        """
        {'type': 'boolean'}
        """
        if (
            enabled
            and app.config.get("USER_USERNAME_PATTERN")
            and not re.match(app.config["USER_USERNAME_PATTERN"], value or "")
        ):
            self._error(field, ERROR_PATTERN)

    def _validate_empty(self, empty, field, value):
        """
        {'type': 'boolean'}
        """
        # let the standard validation happen
        super()._validate_empty(empty, field, value)

        # custom validation
        if isinstance(value, list) or isinstance(value, dict):
            if len(value) == 0 and not empty:
                self._error(field, errors.EMPTY_NOT_ALLOWED)

    def _validate_unique_list(self, unique_list, field, value):
        """
        {'type': 'boolean'}
        """

        if unique_list and isinstance(value, list):
            if len(set(value)) != len(value):
                self._error(field, "Must contain unique items only.")

    def _validate_content_type_single_item_type(self, checked, field, value):
        """
        {'type': 'boolean'}
        """
        if checked and value not in {"text", None}:
            if app.data.find_one("content_types", req=None, item_type=value) is not None:
                self._error(field, _("Only 1 instance is allowed."))
