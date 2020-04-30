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
from eve.io.mongo import Validator
from eve.utils import config
from werkzeug.datastructures import FileStorage
from eve.auth import auth_field_and_value
from cerberus import errors


ERROR_PATTERN = {'pattern': 1}
ERROR_UNIQUE = {'unique': 1}
ERROR_MINLENGTH = {'minlength': 1}
ERROR_REQUIRED = {'required': 1}
ERROR_JSON_LIST = {'json_list': 1}


class SuperdeskValidator(Validator):

    def _validate_mapping(self, mapping, field, value):
        pass

    def _validate_index(self, definition, field, value):
        pass

    def _validate_type_phone_number(self, field, value):
        """Enables validation for `phone_number` schema attribute.

        :param field: field name.
        :param value: field value.
        """
        if not re.match("^(?:(?:0?[1-9][0-9]{8})|(?:(?:\+|00)[1-9][0-9]{9,11}))$", value):
            self._error(field, ERROR_PATTERN)

    def _validate_type_email(self, field, value):
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
        if not re.match('.+@.+', value, re.IGNORECASE):
            self._error(field, ERROR_PATTERN)

    def _validate_type_file(self, field, value):
        """Enables validation for `file` schema attribute."""
        if not isinstance(value, FileStorage):
            self._error(field, ERROR_PATTERN)

    def _validate_multiple_emails(self, multiple, field, value):
        """
        Validates comma separated list of emails.

        :param field: field name.
        :param value: field value.
        """
        if multiple:
            emails = value.split(',')
            for email in emails:
                self._validate_type_email(field, email)

    def _validate_unique(self, unique, field, value):
        """Validate unique with custom error msg."""

        if not self.resource.endswith("autosave") and unique:
            query = {field: value}
            self._set_id_query(query)

            cursor = superdesk.get_resource_service(self.resource).get_from_mongo(req=None, lookup=query)
            if cursor.count():
                self._error(field, ERROR_UNIQUE)

    def _set_id_query(self, query):
        if self._id:
            try:
                query[config.ID_FIELD] = {'$ne': ObjectId(self._id)}
            except Exception:
                query[config.ID_FIELD] = {'$ne': self._id}

    def _validate_iunique(self, unique, field, value):
        """Validate uniqueness ignoring case.MONGODB USE ONLY"""

        if unique:
            pattern = '^{}$'.format(re.escape(value.strip()))
            query = {field: re.compile(pattern, re.IGNORECASE)}
            self._set_id_query(query)

            cursor = superdesk.get_resource_service(self.resource).get_from_mongo(req=None, lookup=query)
            if cursor.count():
                self._error(field, ERROR_UNIQUE)

    def _validate_iunique_per_parent(self, parent_field, field, value):
        """Validate uniqueness ignoring case.MONGODB USE ONLY"""
        original = self._original_document or {}
        update = self.document or {}

        parent_field_value = update.get(parent_field, original.get(parent_field))

        if parent_field:
            pattern = '^{}$'.format(re.escape(value.strip()))
            query = {
                field: re.compile(pattern, re.IGNORECASE),
                parent_field: parent_field_value
            }
            self._set_id_query(query)

            cursor = superdesk.get_resource_service(self.resource).get_from_mongo(req=None, lookup=query)
            if cursor.count():
                self._error(field, ERROR_UNIQUE)

    def _validate_minlength(self, min_length, field, value):
        """Validate minlength with custom error msg."""
        if isinstance(value, (type(''), list)):
            if len(value) < min_length:
                self._error(field, ERROR_MINLENGTH)

    def _validate_required_fields(self, document):
        required = list(field for field, definition in self.schema.items()
                        if definition.get('required') is True)
        missing = set(required) - set(key for key in document.keys()
                                      if document.get(key) is not None or
                                      not self.ignore_none_values)
        for field in missing:
            self._error(field, ERROR_REQUIRED)

    def _validate_type_json_list(self, field, value):
        """It will fail later when loading."""
        if not isinstance(value, type('')):
            self._error(field, ERROR_JSON_LIST)

    def _validate_unique_to_user(self, unique, field, value):
        """Check that value is unique globally or to current user.

        In case 'user' is set within document it will check for unique within
        docs with same 'user' value.

        Otherwise it will check for unique within docs without any 'user' value.
        """
        doc = getattr(self, 'document', getattr(self, 'original_document', {}))

        if 'user' in doc:
            _, auth_value = auth_field_and_value(self.resource)
            query = {'user': auth_value}
        else:
            query = {'user': {'$exists': False}}

        self._is_value_unique(unique, field, value, query)

    def _validate_unique_template(self, unique, field, value):
        """Check that value is unique globally or to current user.

        In case 'is_public' is false within document it will check for unique within
        docs with same 'user' value.

        Otherwise it will check for unique within docs without any 'user' value.
        """
        original = self._original_document or {}
        update = self.document or {}

        is_public = update.get('is_public', original.get('is_public', None))
        template_name = update.get('template_name', original.get('template_name', None))

        if is_public:
            query = {'is_public': True}
        else:
            _, auth_value = auth_field_and_value(self.resource)
            query = {'user': auth_value, 'is_public': False}

        query['template_name'] = re.compile('^{}$'.format(re.escape(template_name.strip())), re.IGNORECASE)

        if self._id:
            id_field = config.DOMAIN[self.resource]['id_field']
            query[id_field] = {'$ne': self._id}

        if superdesk.get_resource_service(self.resource).find_one(req=None, **query):
            self._error(field, "Template Name is not unique")

    def _validate_twitter(self, twitter, field, value):
        """Validator for twitter id e.g `@johnsmith`

        :param field: field name.
        :param value: field value.
        """
        if twitter and value and not re.match('^@[A-Za-z0-9_]{1,15}$', value, re.IGNORECASE):
            self._error(field, ERROR_PATTERN)

    def _validate_empty(self, empty, field, value):
        """Validator for empty list, dict or str"""
        # let the standard validation happen
        super()._validate_empty(empty, field, value)

        # custom validation
        if isinstance(value, list) or isinstance(value, dict):
            if len(value) == 0 and not empty:
                self._error(field, errors.ERROR_EMPTY_NOT_ALLOWED)

    def _validate_unique_list(self, unique_list, field, value):
        """Validate if list contains only unique items."""

        if unique_list and isinstance(value, list):
            if len(set(value)) != len(value):
                self._error(field, "Must contain unique items only.")
