# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from copy import deepcopy
from datetime import datetime, timedelta
import functools
import json
import logging
from superdesk.datalayer import InvalidSearchString
from superdesk.services import BaseService
from superdesk.utc import utcnow
from urllib.parse import urljoin, urlparse, quote

from flask import current_app as app, g
from flask import request
from werkzeug.datastructures import MultiDict

from content_api.app.settings import ELASTIC_DATE_FORMAT
from content_api.errors import BadParameterValueError, UnexpectedParameterError
from content_api.items.resource import ItemsResource
from eve.utils import ParsedRequest, date_to_str
from superdesk import get_resource_service


logger = logging.getLogger('superdesk')


class ItemsService(BaseService):
    """
    A service that knows how to perform CRUD operations on the `item`
    content types.

    Serves mainly as a proxy to the data layer.
    """

    allowed_params = {
        'start_date', 'end_date',
        'include_fields', 'exclude_fields',
        'max_results', 'page', 'version', 'where',
        'q', 'default_operator', 'filter',
        'service', 'subject', 'genre', 'urgency',
        'priority', 'type', 'item_source'
    }

    excluded_fields_from_response = {
        '_etag', '_created',
        '_updated', 'subscribers',
        '_current_version', '_latest_version',
        'ancestors'
    }

    def find_one(self, req, **lookup):
        """Retrieve a specific item.

        :param req: object representing the HTTP request
        :type req: `eve.utils.ParsedRequest`
        :param dict lookup: requested item lookup, contains its ID

        :return: requested item (if found)
        :rtype: dict or None
        """
        if req is None:
            req = ParsedRequest()

        allowed_params = {'include_fields', 'exclude_fields', 'version'}
        self._check_for_unknown_params(
            req, whitelist=allowed_params, allow_filtering=False)

        self._set_fields_filter(req)  # Eve's "projection"

        # if subscribers is not allowed it is an external API request that should be filtered by the user
        if self._is_internal_api():
            # in case there is no subscriber set by auth return nothing
            lookup['subscribers'] = g.get('user')

        return super().find_one(req, **lookup)

    def get(self, req, lookup):
        """Retrieve a list of items that match the filter criteria (if any)
        pssed along the HTTP request.

        :param req: object representing the HTTP request
        :type req: `eve.utils.ParsedRequest`
        :param dict lookup: sub-resource lookup from the endpoint URL

        :return: database results cursor object
        :rtype: `pymongo.cursor.Cursor`
        """
        internal_req = ParsedRequest() if req is None else deepcopy(req)
        internal_req.args = MultiDict()
        orig_request_params = getattr(req, 'args', MultiDict())

        self._check_for_unknown_params(req, whitelist=self.allowed_params)
        self._set_search_field(internal_req.args, orig_request_params)

        # combine elastic search filter for args as args.get('filter')
        self._set_filter_for_arguments(internal_req, orig_request_params)

        # projections
        internal_req.args['exclude_fields'] = orig_request_params.get('exclude_fields')
        internal_req.args['include_fields'] = orig_request_params.get('include_fields')
        self._set_fields_filter(internal_req)  # Eve's "projection"

        # if subscribers is not allowed it is an external API request that should be filtered by the user
        if self._is_internal_api():
            # in case there is no subscriber set by auth return nothing
            lookup['subscribers'] = g.get('user')

        if 'aggregations' in self.allowed_params:
            internal_req.args['aggregations'] = orig_request_params.get('aggregations', 0)

        try:
            res = super().get(internal_req, lookup)
            return res
        except InvalidSearchString:
            raise BadParameterValueError('invalid search text')

    def on_fetched_item(self, document):
        """Event handler when a single item is retrieved from database.

        It triggers the post-processing of the fetched item.

        :param dict document: fetched MongoDB document representing the item
        """
        self._process_fetched_object(document)

    def on_fetched(self, result):
        """Event handler when a collection of items is retrieved from database.

        For each item in the fetched collection it triggers the post-processing
        of it.

        It also changes the default-generated HATEOAS "self" link so that it
        does not expose the internal DB query details, but instead reflects
        what the client has sent in request.

        :param dict result: dictionary contaning the list of MongoDB documents
            (the fetched items) and some metadata, e.g. pagination info
        """
        for document in result['_items']:
            self._process_fetched_object(document)

        if '_links' in result:  # might not be present if HATEOAS disabled
            url_parts = urlparse(request.url)
            result['_links']['self']['href'] = '{}?{}'.format(
                url_parts.path[1:],  # relative path, remove opening slash
                url_parts.query
            )

    def on_deleted(self, document):
        """Event handler when an item has been deleted.

        Make sure that all associated item versions are delete as well.

        :param dict document: Item that has been deleted
        """
        get_resource_service('items_versions').on_item_deleted(document)

    def get_expired_items(self, expiry_datetime=None, expiry_days=None, max_results=None, include_children=True):
        """Get the expired items.

        Returns a generator for the list of expired items, sorting by `_id` and returning `max_results` per iteration.

        :param datetime expiry_datetime: Expiry date/time used to retrieve the list of items, defaults to `utcnow()`
        :param int expiry_days: Number of days content expires, defaults to `CONTENT_API_EXPIRY_DAYS`
        :param int max_results: Maximum results to retrieve per iteration, defaults to `MAX_EXPIRY_QUERY_LIMIT`
        :param boolean include_children: Include only root item if False, otherwise include the entire item chain
        :return list: expired content_api items
        """

        if expiry_datetime is None:
            expiry_datetime = utcnow()

        if expiry_days is None:
            expiry_days = app.settings['CONTENT_API_EXPIRY_DAYS']

        if max_results is None:
            max_results = app.settings['MAX_EXPIRY_QUERY_LIMIT']

        last_id = None
        expire_at = date_to_str(expiry_datetime - timedelta(days=expiry_days))

        while True:
            query = {'$and': [{'_updated': {'$lte': expire_at}}]}

            if last_id is not None:
                query['$and'].append({'_id': {'$gt': last_id}})

            if not include_children:
                query['$and'].append({'ancestors': {'$exists': False}})

            req = ParsedRequest()
            req.sort = '_id'
            req.where = json.dumps(query)
            req.max_results = max_results

            items = list(self.get_from_mongo(req=req, lookup=None))

            if not items:
                break

            last_id = items[-1]['_id']
            yield items

    def _is_internal_api(self):
        """Check if request is for internal search_capi endpoint or external items endpoint

        :return bool:
        """
        return self.datasource == 'items' or self.datasource == 'packages'

    def _process_fetched_object(self, document):
        """Does some processing on the raw document fetched from database.

        It sets the item's `uri` field and removes all the fields added by the
        `Eve` framework that are not part of the NINJS standard (except for
        the HATEOAS `_links` object).
        It also sets the URLs for all externally referenced media content.

        :param dict document: MongoDB document to process
        """
        document['uri'] = self._get_uri(document)

        _id = document.pop('_id')

        for field_name in self.excluded_fields_from_response:
            document.pop(field_name, None)

        self._process_item_renditions(document)
        self._process_item_associations(document)
        get_resource_service('api_audit').audit_item(document, _id)

    def _process_item_renditions(self, item):
        hrefs = {}
        if item.get('renditions'):
            for _k, v in item['renditions'].items():
                if 'media' in v:
                    href = v.get('href')
                    media = v.pop('media')
                    v['href'] = app.media.url_for_media(media, v.get('mimetype'))
                    hrefs[href] = v['href']
        return hrefs

    def _process_item_associations(self, item):
        hrefs = {}
        allowed_items = {}
        if item.get('associations'):
            for _k, v in item.get('associations', {}).items():
                # only allow subscribers
                if (g.get('subscriber') or g.get('user')) in v.get('subscribers', []):
                    hrefs.update(self._process_item_renditions(v))
                    v.pop('subscribers', None)
                    allowed_items[_k] = v

        item['associations'] = allowed_items

        if item.get('body_html'):
            for k, v in hrefs.items():
                item['body_html'] = item['body_html'].replace(k, v)

    def _get_uri(self, document):
        """Return the given document's `uri`.

        :param dict document: MongoDB document fetched from database
        """
        if document.get('type') == 'composite':
            endpoint_name = 'packages'
        else:
            endpoint_name = 'items'

        resource_url = '{api_url}/{endpoint}/'.format(
            api_url=app.config['CONTENTAPI_URL'],
            endpoint=app.config['URLS'][endpoint_name]
        )

        return urljoin(resource_url, quote(document.get('_id', document.get('guid'))))

    def _check_for_unknown_params(
        self, request, whitelist, allow_filtering=True
    ):
        """Check if the request contains only allowed parameters.

        :param req: object representing the HTTP request
        :type req: `eve.utils.ParsedRequest`
        :param whitelist: iterable containing the names of allowed parameters.
        :param bool allow_filtering: whether or not the filtering parameter is
            allowed (True by default). Used for disallowing it when retrieving
            a single object.

        :raises UnexpectedParameterError:
            * if the request contains a parameter that is not whitelisted
            * if the request contains more than one value for any of the
              parameters
        """
        if not request or not getattr(request, 'args'):
            return
        request_params = request.args or MultiDict()

        if not allow_filtering:
            err_msg = ("Filtering{} is not supported when retrieving a "
                       "single object (the \"{param}\" parameter)")

            if 'start_date' in request_params.keys():
                desc = err_msg.format(' by date range', param='start_date')
                raise UnexpectedParameterError(desc=desc)

            if 'end_date' in request_params.keys():
                desc = err_msg.format(' by date range', param='end_date')
                raise UnexpectedParameterError(desc=desc)

        for param_name in request_params.keys():
            if param_name not in whitelist:
                raise UnexpectedParameterError(
                    desc="Unexpected parameter ({})".format(param_name)
                )

            if len(request_params.getlist(param_name)) > 1:
                desc = "Multiple values received for parameter ({})"
                raise UnexpectedParameterError(desc=desc.format(param_name))

    def _set_filter_for_arguments(self, req, orig_request_params):
        """Based on arguments creates elastic search filters and
        assign to `filter` argument of the `req` object.

        :param req: object representing the HTTP request
        :type req: `eve.utils.ParsedRequest`
        :param dict orig_request_params: request parameter names and their
            corresponding values
        """
        # request argments and elasticsearch fields
        argument_fields = {
            'service': 'service.code',
            'subject': 'subject.code',
            'urgency': 'urgency',
            'priority': 'priority',
            'genre': 'genre.code',
            'item_source': 'source'
        }

        try:
            filters = json.loads(orig_request_params.get('filter')) \
                if orig_request_params and orig_request_params.get('filter') else []
        except:
            raise BadParameterValueError("Bad parameter value for Parameter (filter)")

        for argument_name, field_name in argument_fields.items():
            if argument_name not in orig_request_params or orig_request_params.get(argument_name) is None:
                continue

            filter_value = orig_request_params.get(argument_name)
            try:
                filter_value = json.loads(orig_request_params.get(argument_name))
            except:
                pass

            if not filter_value:
                raise BadParameterValueError("Bad parameter value for Parameter ({})".format(argument_name))

            if not isinstance(filter_value, list):
                filter_value = [filter_value]

            filters.append({'terms': {field_name: filter_value}})

        # set the date range filter
        start_date, end_date = self._get_date_range(orig_request_params)
        date_filter = self._create_date_range_filter(start_date, end_date)
        if date_filter:
            filters.append(date_filter)
        if filters:
            req.args['filter'] = json.dumps({'bool': {'must': filters}})

    def _get_date_range(self, request_params):
        """Extract the start and end date limits from request parameters.

        If start and/or end date parameter is not present, a default value is
        returned for the missing parameter(s).

        :param dict request_params: request parameter names and their
            corresponding values

        :return: a (start_date, end_date) tuple with both values being
            instances of Python's datetime.date

        :raises BadParameterValueError:
            * if any of the dates is not in the ISO 8601 format
            * if any of the dates is set in the future
            * if the start date is bigger than the end date
        """
        # check date limits' format...
        err_msg = ("{} parameter must be a valid ISO 8601 date (YYYY-MM-DD) "
                   "without the time part")

        try:
            start_date = self._parse_iso_date(request_params.get('start_date'))
        except ValueError:
            raise BadParameterValueError(
                desc=err_msg.format('start_date')) from None

        try:
            end_date = self._parse_iso_date(request_params.get('end_date'))
        except ValueError:
            raise BadParameterValueError(
                desc=err_msg.format('end_date')) from None

        # disallow dates in the future...
        err_msg = (
            "{} date ({}) must not be set in the future "
            "(current server date (UTC): {})")
        today = utcnow().date()

        if (start_date is not None) and (start_date > today):
            raise BadParameterValueError(
                desc=err_msg.format(
                    'Start', start_date.isoformat(), today.isoformat()
                )
            )

        if (end_date is not None) and (end_date > today):
            raise BadParameterValueError(
                desc=err_msg.format(
                    'End', end_date.isoformat(), today.isoformat()
                )
            )

        # make sure that the date range limits make sense...
        if (
            (start_date is not None) and (end_date is not None) and
            (start_date > end_date)
        ):
            # NOTE: we allow start_date == end_date (for specific date queries)
            raise BadParameterValueError(
                desc="Start date must not be greater than end date")

        # set default date range values if missing...
        if self._is_internal_api():
            if end_date is None:
                end_date = today

            if start_date is None:
                start_date = end_date - timedelta(days=7)  # get last 7 days by default

        return start_date, end_date

    def _create_date_range_filter(self, start_date, end_date):
        """Create a MongoDB date range query filter from the given dates.

        If both the start date and the end date are None, an empty filter is
        returned. The filtering is performed on the `versioncreated` field in
        database.

        :param start_date: the minimum version creation date (inclusive)
        :type start_date: datetime.date or None
        :param end_date: the maximum version creation date (inclusive)
        :type end_date: datetime.date or None

        :return: MongoDB date range filter (as a dictionary)
        """
        if (start_date is None) and (end_date is None):
            return {}  # nothing to set for the date range filter

        if end_date is None:
            end_date = utcnow().date()

        date_filter = {'range': {'versioncreated': {}}}

        date_filter['range']['versioncreated']['gte'] = self._format_date(start_date)
        date_filter['range']['versioncreated']['lte'] = self._format_date(end_date)

        return date_filter

    def _set_filter_parameter(self, req, filter, original_filter_param):
        elastic_filter = []
        try:
            elastic_filter = json.loads(original_filter_param) if original_filter_param else []
            if not isinstance(elastic_filter, list):
                raise BadParameterValueError(desc='Invalid Parameter value for filter')
        except:
            raise BadParameterValueError(desc='Invalid Parameter value for filter')

        elastic_filter.append(filter)
        req.args['filter'] = json.dumps(elastic_filter)

    def _set_fields_filter(self, req):
        """Set content fields filter on the request object (the "projection")
        based on the request parameters.

        It causes some of the content fields to be excluded from the retrieved
        data.

        :param req: object representing the HTTP request
        :type req: `eve.utils.ParsedRequest`
        :param dict original_request_params: request parameter names and their
            corresponding values
        """
        request_params = req.args or {}

        include_fields, exclude_fields = self._get_field_filter_params(request_params)
        projection = self._create_field_filter(include_fields, exclude_fields)

        req.projection = json.dumps(projection)

    def _set_search_field(self, internal_request_params, original_request_params):
        if internal_request_params is None:
            internal_request_params = MultiDict()

        for key, value in original_request_params.items():
            if key in {'q', 'default_operator', 'df', 'filter'}:
                internal_request_params[key] = value

    def _get_field_filter_params(self, request_params):
        """Extract the list of content fields to keep in or remove from
        the response.

        The parameter names are `include_fields` and `exclude_fields`. Both are
        simple comma-separated lists, for example::

            exclude_fields=  field_1, field_2,field_3,, ,field_4,

        NOTE: any redundant spaces, empty field values and duplicate values are
        gracefully ignored and do not cause an error.

        :param dict request_params: request parameter names and their
            corresponding values

        :return: a (include_fields, exclude_fields) tuple with each item being
            either a `set` of field names (as strings) or None if the request
            does not contain the corresponding parameter

        :raises BadParameterValueError:
            * if the request contains both parameters at the same time
            * if any of the parameters contain an unknown field name (i.e. not
                defined in the resource schema)
            * if `exclude_params` parameter contains a field name that is
                required to be present in the response according to the NINJS
                standard
        """
        include_fields = request_params.get('include_fields')
        exclude_fields = request_params.get('exclude_fields')

        # parse field filter parameters...
        strip_items = functools.partial(map, lambda s: s.strip())
        remove_empty = functools.partial(filter, None)

        if include_fields is not None:
            include_fields = include_fields.split(',')
            include_fields = set(remove_empty(strip_items(include_fields)))

        if exclude_fields is not None:
            exclude_fields = exclude_fields.split(',')
            exclude_fields = set(remove_empty(strip_items(exclude_fields)))

        # check for semantically incorrect field filter values...
        if (include_fields is not None) and (exclude_fields is not None):
            err_msg = ('Cannot both include and exclude content fields '
                       'at the same time.')
            raise UnexpectedParameterError(desc=err_msg)

        if include_fields is not None:
            err_msg = 'Unknown content field to include ({}).'
            for field in include_fields:
                if field not in ItemsResource.schema:
                    raise BadParameterValueError(desc=err_msg.format(field))

        if exclude_fields is not None:
            if 'uri' in exclude_fields:
                err_msg = ('Cannot exclude a content field required by the '
                           'NINJS format (uri).')
                raise BadParameterValueError(desc=err_msg)

            err_msg = 'Unknown content field to exclude ({}).'
            for field in exclude_fields:
                if field not in ItemsResource.schema:
                    raise BadParameterValueError(desc=err_msg.format(field))

        return include_fields, exclude_fields

    def _create_field_filter(self, include_fields, exclude_fields):
        """Create an `Eve` projection object that explicitly includes/excludes
        particular content fields from results.

        At least one of the parameters *must* be None. The created projection
        uses either a whitlist or a blacklist approach (see below), it cannot
        use both at the same time.

        * If `include_fields` is not None, a blacklist approach is used. All
            fields are _omittted_ from the result, except for those listed in
            the `include_fields` set.
        * If `exclude_fields` is not None, a whitelist approach is used. All
            fields are _included_ in the result, except for those listed in the
            `exclude_fields` set.
        * If both parameters are None, no field filtering should be applied
        and an empty dictionary is returned.

        NOTE: fields required by the NINJS standard are _always_ included in
        the result, regardless of the field filtering parameters.

        :param include_fields: fields to explicitly include in result
        :type include_fields: set of strings or None
        :param exclude_fields: fields to explicitly exclude from result
        :type exclude_fields: set of strings or None

        :return: `Eve` projection filter (as a dictionary)
        """
        projection = {}

        if include_fields is not None:
            for field in include_fields:
                projection[field] = 1
        elif exclude_fields is not None:
            for field in exclude_fields:
                projection[field] = 0

        return projection

    @staticmethod
    def _parse_iso_date(date_str):
        """Create a date object from the given string in ISO 8601 format.

        :param date_str:
        :type date_str: str or None

        :return: resulting date object or None if None is given
        :rtype: datetime.date

        :raises ValueError: if `date_str` is not in the ISO 8601 date format
        """
        if date_str is None:
            return None
        else:
            return datetime.strptime(date_str, '%Y-%m-%d').date()

    @staticmethod
    def _format_date(date):
        return datetime.strftime(date, ELASTIC_DATE_FORMAT)
