# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from content_api.items.service import ItemsService
from flask import g

from superdesk import get_resource_privileges
from superdesk.errors import SuperdeskApiError


class SearchService(ItemsService):
    """This class wraps the external Items API endpoint implemented by ItemsService but will allow the filtering by
    subscriber and the return of aggregates
    """

    # Usage is something like :-
    #  http://localhost:5000/api/search_capi?where={"headline":"muppets"}&start_date=1975-12-31
    #        &subscribers=558384d31d41c849d9614500
    #
    #    or for all subscribers
    #    http://localhost:5000/api/search_capi?where={"headline":"muppets"}&start_date=1975-12-31

    allowed_params = {
        'start_date', 'end_date',
        'include_fields', 'exclude_fields',
        'max_results', 'page',
        'where', 'version',
        'subscribers', 'aggregations',
        'q', 'default_operator', 'sort', 'filter',
        'service', 'subject', 'genre', 'urgency',
        'priority', 'type', 'item_source'
    }

    excluded_fields_from_response = {}

    def _filter_empty_vals(self, data):
        """Filter out `None` values from a given dict."""
        return dict(filter(lambda x: x[1], data.items()))

    def _format_cv_item(self, item):
        return self._filter_empty_vals({
            'qcode': item.get('code'),
            'name': item.get('name'),
        })

    def _map_response(self, response):
        """
        Map the fields names that are changed as part of the ninjs formatting back to the internal values
        :param response:
        :return:
        """
        if not response:
            return None

        for item in response:
            self._map_item(item)

        return response

    def _map_item(self, item):
        """Maps the associations.
        :param dict item:
        :return:
        """
        if not item:
            return

        if item.get('service'):
            item['anpa_category'] = [self._format_cv_item(item) for item in (item.get('service') or [])]
            item.pop('service')

        if item.get('subject'):
            item['subject'] = [self._format_cv_item(item) for item in (item.get('subject') or [])]

        if item.get('genre'):
            item['genre'] = [self._format_cv_item(item) for item in (item.get('genre') or [])]

        if item.get('place'):
            item['place'] = [self._format_cv_item(item) for item in (item.get('place') or [])]

        if item.get('signal'):
            item['flags'] = {'marked_for_legal': True for signal in item.get('signal')
                             if signal.get('code') == 'cwarn'}

    def find_one(self, req, **lookup):
        self.check_get_access_privilege()
        response = super().find_one(req, **lookup)
        self._map_item(response)
        return response

    def get(self, req, lookup):
        # if there is a subscriber argumment map it into the lookup
        self.check_get_access_privilege()
        if req and req.args and req.args.get('subscribers'):
            lookup = {'subscribers': req.args.get('subscribers')}
            g.subscriber = req.args.get('subscribers')

        response = super().get(req, lookup)
        if response.count() > 0:
            return self._map_response(response)
        return response

    def _process_fetched_object(self, document):
        """Does some processing on the raw document fetched from database.

        It sets the item's `uri` field and removes all the fields added by the
        `Eve` framework that are not part of the NINJS standard (except for
        the HATEOAS `_links` object).
        It also sets the URLs for all externally referenced media content.

        :param dict document: MongoDB document to process
        """
        self._process_item_renditions(document)
        self._process_item_associations(document)
        self._map_associations(document)

    def _map_associations(self, item):
        """Map association response.

        :param dict item:
        """
        allowed_items = {}
        if item.get('associations'):
            for k, v in item.get('associations', {}).items():
                if v is None:
                    continue
                self._map_item(v)
                v['_id'] = v.get('guid', v.get('_id'))
                allowed_items[k] = v

        item['associations'] = allowed_items

    def check_get_access_privilege(self):
        """Checks if user is authorized to perform get operation on search api.

        If authorized then request is
        forwarded otherwise throws forbidden error.

        :raises: SuperdeskApiError.forbiddenError() if user is unauthorized to access the Legal Archive resources.
        """

        if not hasattr(g, 'user'):
            return

        privileges = g.user.get('active_privileges', {})
        resource_privileges = get_resource_privileges(self.datasource).get('GET', None)
        if privileges.get(resource_privileges, 0) == 0:
            raise SuperdeskApiError.forbiddenError()
