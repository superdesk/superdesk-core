# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license
from superdesk import get_resource_service
from superdesk.services import BaseService
from superdesk.errors import SuperdeskApiError
from superdesk.publish.formatters import get_all_formatters
from superdesk.utils import ListCursor
from eve.validation import ValidationError
from apps.publish.content.common import ITEM_PUBLISH


class FormattersService(BaseService):

    def get(self, req, lookup):
        formatters = get_all_formatters()
        return ListCursor([{'name': type(f).__name__} for f in formatters])

    def _get_formatter(self, name):
        formatters = get_all_formatters()
        return next((f for f in formatters if type(f).__name__ == name), None)

    def _validate(self, doc):
        """Validates the given story for publish action"""
        validate_item = {'act': ITEM_PUBLISH, 'type': doc['type'], 'validate': doc}
        validation_errors = get_resource_service('validate').post([validate_item])
        if validation_errors[0]:
            raise ValidationError(validation_errors)

    def create(self, docs, **kwargs):
        service = get_resource_service('archive')
        doc = docs[0]
        formatter_name = doc.get('formatter_name')

        if not formatter_name:
            raise SuperdeskApiError.badRequestError('Formatter name not found')

        formatter = self._get_formatter(formatter_name)

        if not formatter:
                raise SuperdeskApiError.badRequestError('Formatter not found')

        if 'article_id' in doc:
            article_id = doc.get('article_id')
            article = service.find_one(req=None, _id=article_id)

            if not article:
                raise SuperdeskApiError.badRequestError('Article not found!')

            try:
                self._validate(article)
                sequence, formatted_doc = formatter.format(article, {'_id': '0'}, None)[0]
                formatted_doc = formatted_doc.replace('\'\'', '\'')
            except Exception as ex:
                raise SuperdeskApiError.\
                    badRequestError('Error in formatting article: {}'.format(str(ex)))

            return [{'formatted_doc': formatted_doc}]
