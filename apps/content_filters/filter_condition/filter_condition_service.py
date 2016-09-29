# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license
import logging
import re
from superdesk.errors import SuperdeskApiError
from superdesk import get_resource_service
from superdesk.services import BaseService

logger = logging.getLogger(__name__)


class FilterConditionService(BaseService):
    def on_create(self, docs):
        self._check_equals(docs)
        self._check_parameters(docs)

    def on_update(self, updates, original):
        doc = dict(original)
        doc.update(updates)
        self._check_equals([doc])
        self._check_parameters([doc])

    def delete(self, lookup):
        referenced_filters = self._get_referenced_filter_conditions(lookup.get('_id'))
        if referenced_filters.count() > 0:
            references = ','.join([pf['name'] for pf in referenced_filters])
            raise SuperdeskApiError.badRequestError('Filter condition has been referenced in pf:{}'.format(references))
        return super().delete(lookup)

    def _get_referenced_filter_conditions(self, id):
        lookup = {'content_filter.expression.fc': [id]}
        content_filters = get_resource_service('content_filters').get(req=None, lookup=lookup)
        return content_filters

    def _check_parameters(self, docs):
        parameters = get_resource_service('filter_condition_parameters').get(req=None, lookup=None)
        for doc in docs:
            parameter = [p for p in parameters if p['field'] == doc['field']]
            if not parameter or len(parameter) == 0:
                raise SuperdeskApiError.badRequestError(
                    'Filter condition:{} has unidentified field: {}'
                    .format(doc['name'], doc['field']))
            if doc['operator'] not in parameter[0]['operators']:
                raise SuperdeskApiError.badRequestError(
                    'Filter condition:{} has unidentified operator: {}'
                    .format(doc['name'], doc['operator']))

    def _check_equals(self, docs):
        """Checks if any of the filter conditions in the docs already exists

        :param docs: List of filter conditions to be tested
        :raises SuperdeskApiError: if any of the filter conditions in the docs
        already exists
        """
        for doc in docs:
            existing_docs = self.get(None, {'field': doc['field'], 'operator': doc['operator']})
            for existing_doc in existing_docs:
                if '_id' in doc and doc['_id'] == existing_doc['_id']:
                    continue
                if self._are_equal(doc, existing_doc):
                    raise SuperdeskApiError.badRequestError(
                        'Filter condition:{} has identical settings'.format(existing_doc['name']))

    def check_similar(self, filter_condition):
        """Checks for similar items

        Checks if the given filter condition already exists (for text fields like headline) or
        if there's any other filter condition that contains the given filter
        condition (for controlled vocabulary fields like urgency).
        For example: if filter_condition ['urgency' in 3,4] exists and if
        filter condition ['urgency' in 3] is searched we'll have a match

        :param filter_condition: Filter conditions to be tested
        :return: Returns the list of matching filter conditions
        """
        parameters = get_resource_service('filter_condition_parameters').get(req=None, lookup=None)
        parameter = [p for p in parameters if p['field'] == filter_condition['field']]
        if parameter[0]['operators'] == ['in', 'nin']:
            # this is a controlled vocabulary field so find the overlapping values
            existing_docs = list(self.get(None,
                                          {'field': filter_condition['field'],
                                           'operator': filter_condition['operator'],
                                           'value': {'$regex': re.compile('.*{}.*'.format(filter_condition['value']),
                                                                          re.IGNORECASE)}}))
            parameter[0]['operators'].remove(filter_condition['operator'])
            existing_docs.extend(list(self.get(None,
                                               {'field': filter_condition['field'],
                                                'operator': parameter[0]['operators'][0],
                                                'value': {'$not': re.compile('.*{}.*'.format(filter_condition['value']),
                                                                             re.IGNORECASE)}})))
        else:
            # find the exact matches
            existing_docs = list(self.get(None, {'field': filter_condition['field'],
                                                 'operator': filter_condition['operator'],
                                                 'value': {'$regex': re.compile('{}'.format(filter_condition['value']),
                                                                                re.IGNORECASE)}}))
        return existing_docs

    def _are_equal(self, fc1, fc2):
        def get_comparer(fc):
            return ''.join(sorted(fc['value'].upper())) if ',' in fc['value'] else fc['value'].upper()

        return all([fc1['field'] == fc2['field'],
                    fc1['operator'] == fc2['operator'],
                    get_comparer(fc1) == get_comparer(fc2)])
