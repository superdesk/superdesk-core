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


class SearchService(ItemsService):
    """This class wraps the external Items API endpoint implimented by ItemsService but will allow the filtering by
    subsciber and the return of aggregates
    """

    # Uasge is something like :-
    #  http://localhost:5000/api/search_api?where={"headline":"muppets"}&start_date=1975-12-31
    #        &subscribers=558384d31d41c849d9614500
    #
    #    or for all subscribers
    #    http://localhost:5000/api/search_api?where={"headline":"muppets"}&start_date=1975-12-31

    allowed_params = {
        'start_date', 'end_date',
        'include_fields', 'exclude_fields',
        'max_results', 'page',
        'where',
        'version',
        'subscribers',
        'aggregations'
    }

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
        for item in response:
            if item.get('service'):
                item['anpa_category'] = [self._format_cv_item(item) for item in item.get('service', [])]
                item.pop('service')

            if item.get('subject'):
                item['subject'] = [self._format_cv_item(item) for item in item.get('subject', [])]

            if item.get('genre'):
                item['genre'] = [self._format_cv_item(item) for item in item.get('genre', [])]

            if item.get('place'):
                item['place'] = [self._format_cv_item(item) for item in item.get('place', [])]

        if response.hits.get('aggregations') and 'category' in response.hits.get('aggregations', {}):
            response.hits.get('aggregations')['anpa_category'] = response.hits.get('aggregations').get('category', {})
            response.hits.get('aggregations').pop('category')

        return response

    def get(self, req, lookup):
        # if there is a subscriber argumment map it into the lookup
        if req and req.args and req.args.get('subscribers'):
            lookup = {'subscribers': req.args.get('subscribers')}
        response = super().get(req, lookup)
        if response.count() > 0:
            return self._map_response(response)
        return response
