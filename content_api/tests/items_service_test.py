# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import json
from datetime import date, timedelta
from eve.utils import ParsedRequest
from flask import Flask
from unittest import mock
from unittest.mock import MagicMock
from werkzeug.datastructures import MultiDict
from superdesk import resources
from content_api.tests import ApiTestCase
from superdesk.tests import TestCase
from superdesk.utc import utcnow
from superdesk import get_resource_service


class FakeAuditService():

    def audit_item(self, doc, id):
        return


class FakeAuditResource():
    service = None

    def __init__(self, service):
        self.service = service


class ItemsServiceTestCase(ApiTestCase):
    """Base class for the `items` service tests."""

    def setUp(self):
        self.app = Flask(__name__)
        self.ctx = self.app.test_request_context('/')
        self.ctx.push()
        resources['api_audit'] = FakeAuditResource(FakeAuditService())

    def tearDown(self):
        self.ctx.pop()

    def _get_target_class(self):
        """Return the class under test.

        Make the test fail immediately if the class cannot be imported.
        """
        try:
            from content_api.items import ItemsService
        except ImportError:
            self.fail("Could not import class under test (ItemsService).")
        else:
            return ItemsService

    def _make_one(self, *args, **kwargs):
        """Create a new instance of the class under test."""
        kwargs['datasource'] = 'items'
        return self._get_target_class()(*args, **kwargs)


class CheckForUnknownParamsMethodTestCase(ItemsServiceTestCase):
    """Tests for the _check_for_unknown_params() helper method."""

    def test_does_not_raise_an_error_on_valid_parameters(self):
        request = MagicMock()
        request.args = MultiDict([('sort_by', 'language')])
        instance = self._make_one()

        try:
            instance._check_for_unknown_params(request, ('foo', 'sort_by', 'bar'))
        except Exception as ex:
            self.fail("Exception unexpectedly raised ({})".format(ex))

    def test_raises_correct_error_on_unexpected_parameters(self):
        request = MagicMock()
        request.args = MultiDict([('param_x', 'something')])

        from content_api.errors import UnexpectedParameterError
        instance = self._make_one()

        with self.assertRaises(UnexpectedParameterError) as context:
            instance._check_for_unknown_params(request, ('foo', 'bar'))

        ex = context.exception
        self.assertEqual(ex.payload, 'Unexpected parameter (param_x)')

    def test_raises_descriptive_error_on_filtering_disabled(self):
        request = MagicMock()
        request.args = MultiDict([('q', '{"language": "en"}')])

        from content_api.errors import UnexpectedParameterError
        instance = self._make_one()

        with self.assertRaises(UnexpectedParameterError) as context:
            instance._check_for_unknown_params(
                request, whitelist=(), allow_filtering=False)

        ex = context.exception
        self.assertEqual(
            ex.payload,
            'Unexpected parameter (q)'
        )

    def test_raises_descriptive_error_on_disabled_start_date_filtering(self):
        request = MagicMock()
        request.args = MultiDict([('start_date', '2015-01-01')])

        from content_api.errors import UnexpectedParameterError
        instance = self._make_one()

        with self.assertRaises(UnexpectedParameterError) as context:
            instance._check_for_unknown_params(
                request, whitelist=(), allow_filtering=False)

        ex = context.exception
        self.assertEqual(
            ex.payload,
            'Filtering by date range is not supported when retrieving a '
            'single object (the "start_date" parameter)'
        )

    def test_raises_descriptive_error_on_disabled_end_date_filtering(self):
        request = MagicMock()
        request.args = MultiDict([('end_date', '2015-01-01')])

        from content_api.errors import UnexpectedParameterError
        instance = self._make_one()

        with self.assertRaises(UnexpectedParameterError) as context:
            instance._check_for_unknown_params(
                request, whitelist=(), allow_filtering=False)

        ex = context.exception
        self.assertEqual(
            ex.payload,
            'Filtering by date range is not supported when retrieving a '
            'single object (the "end_date" parameter)'
        )

    def test_raises_correct_error_on_duplicate_parameters(self):
        request = MagicMock()
        request.args = MultiDict([('foo', 'value 1'), ('foo', 'value 2')])

        from content_api.errors import UnexpectedParameterError
        instance = self._make_one()

        with self.assertRaises(UnexpectedParameterError) as context:
            instance._check_for_unknown_params(request, whitelist=('foo',))

        ex = context.exception
        self.assertEqual(
            ex.payload, "Multiple values received for parameter (foo)")


fake_super_get = MagicMock(name='fake super().get')


@mock.patch('content_api.items.service.BaseService.get', fake_super_get)
class GetMethodTestCase(ItemsServiceTestCase):
    """Tests for the get() method."""

    def setUp(self):
        super().setUp()
        fake_super_get.reset_mock()

    @mock.patch('content_api.items.service.ItemsService._check_for_unknown_params')
    def test_correctly_invokes_parameter_validation(self, fake_check_unknown):
        fake_request = MagicMock()
        fake_request.args = MultiDict()
        lookup = {}

        instance = self._make_one()
        instance.get(fake_request, lookup)

        self.assertTrue(fake_check_unknown.called)
        args, kwargs = fake_check_unknown.call_args

        self.assertGreater(len(args), 0)
        self.assertEqual(args[0], fake_request)

        expected_whitelist = sorted([
            'start_date', 'end_date',
            'include_fields', 'exclude_fields',
            'max_results', 'page', 'version', 'where',
            'q', 'default_operator', 'filter',
            'service', 'subject', 'genre', 'urgency',
            'priority', 'type', 'item_source'
        ])

        whitelist_arg = kwargs.get('whitelist')
        if whitelist_arg is not None:
            # NOTE: the whitelist argument is converted to a list, because any
            # iterable type is valid, not just lists
            self.assertEqual(sorted(list(whitelist_arg)), expected_whitelist)
        else:
            # whitelist can also be passed as a positional argument
            self.assertGreater(len(args), 1)
            self.assertEqual(sorted(list(args[1])), expected_whitelist)

    @mock.patch('content_api.items.service.ItemsService._set_fields_filter')
    def test_sets_fields_filter_on_request_object(self, fake_set_fields_filter):
        fake_request = MagicMock()
        fake_request.args = MultiDict()
        fake_request.projection = {}
        lookup = {}

        instance = self._make_one()
        instance.get(fake_request, lookup)

        self.assertTrue(fake_set_fields_filter.called)
        args, _ = fake_set_fields_filter.call_args

        self.assertGreater(len(args), 0)
        self.assertEqual(args[0].projection, {})

    def test_provides_request_object_to_superclass_if_not_given(self):
        lookup = {}

        instance = self._make_one()
        instance.get(None, lookup)

        self.assertTrue(fake_super_get.called)
        args, _ = fake_super_get.call_args
        self.assertEqual(len(args), 2)
        self.assertIsInstance(args[0], ParsedRequest)

    def test_raises_correct_error_on_invalid_start_date_parameter(self):
        request = MagicMock()
        request.args = MultiDict([('start_date', '2015-13-35')])
        lookup = {}

        from content_api.errors import BadParameterValueError
        instance = self._make_one()

        with self.assertRaises(BadParameterValueError) as context:
            instance.get(request, lookup)

        ex = context.exception
        self.assertEqual(
            ex.payload,
            ("start_date parameter must be a valid ISO 8601 date (YYYY-MM-DD) "
             "without the time part"))

    def test_raises_correct_error_on_invalid_end_date_parameter(self):
        request = MagicMock()
        request.args = MultiDict([('end_date', '2015-13-35')])
        lookup = {}

        from content_api.errors import BadParameterValueError
        instance = self._make_one()

        with self.assertRaises(BadParameterValueError) as context:
            instance.get(request, lookup)

        ex = context.exception
        self.assertEqual(
            ex.payload,
            ("end_date parameter must be a valid ISO 8601 date (YYYY-MM-DD) "
             "without the time part"))

    def test_raises_correct_error_if_start_date_greater_than_end_date(self):
        request = MagicMock()
        request.args = MultiDict([
            ('start_date', '2015-02-17'),
            ('end_date', '2015-02-16')
        ])
        lookup = {}

        from content_api.errors import BadParameterValueError
        instance = self._make_one()

        with self.assertRaises(BadParameterValueError) as context:
            instance.get(request, lookup)

        ex = context.exception
        self.assertEqual(
            ex.payload, "Start date must not be greater than end date")

    def test_allows_start_and_end_dates_to_be_equal(self):
        request = MagicMock()
        request.args = MultiDict([
            ('start_date', '2010-01-28'),
            ('end_date', '2010-01-28')
        ])
        lookup = {}
        instance = self._make_one()

        try:
            instance.get(request, lookup)
        except Exception as ex:
            self.fail("Exception unexpectedly raised ({})".format(ex))

    def test_includes_given_date_range_into_query_filter_if_given(self):
        request = MagicMock()
        request.args = MultiDict([
            ('start_date', '2012-08-21'),
            ('end_date', '2012-08-26')
        ])
        lookup = {}

        instance = self._make_one()
        instance.get(request, lookup)

        self.assertTrue(fake_super_get.called)
        args, _ = fake_super_get.call_args
        self.assertGreater(len(args), 0)

        filters = json.loads(args[0].args['filter'])['bool']['must']
        date_filter = filters[0].get('range', {}).get('versioncreated', {})
        expected_filter = {
            'gte': '2012-08-21',
            'lte': '2012-08-26'
        }
        self.assertEqual(date_filter, expected_filter)

    @mock.patch('content_api.items.service.utcnow')
    def test_sets_end_date_to_today_if_not_given(self, fake_utcnow):
        request = MagicMock()
        request.args = MultiDict([('start_date', '2012-08-21')])
        lookup = {}

        fake_utcnow.return_value.date.return_value = date(2014, 7, 15)

        instance = self._make_one()
        instance.get(request, lookup)

        self.assertTrue(fake_super_get.called)
        args, _ = fake_super_get.call_args
        self.assertGreater(len(args), 0)

        filters = json.loads(args[0].args['filter'])['bool']['must']
        date_filter = filters[0].get('range', {}).get('versioncreated', {})
        expected_filter = {
            'gte': '2012-08-21',
            'lte': '2014-07-15'
        }
        self.assertEqual(date_filter, expected_filter)

    def test_sets_start_date_equal_to_end_date_if_not_given(self):
        request = MagicMock()
        request.args = MultiDict([('end_date', '2012-08-21')])
        lookup = {}

        instance = self._make_one()
        instance.get(request, lookup)

        self.assertTrue(fake_super_get.called)
        args, _ = fake_super_get.call_args
        self.assertGreater(len(args), 0)

        filters = json.loads(args[0].args['filter'])['bool']['must']
        date_filter = filters[0].get('range', {}).get('versioncreated', {})
        expected_filter = {
            'gte': '2012-08-14',
            'lte': '2012-08-21'
        }
        self.assertEqual(date_filter, expected_filter)

    @mock.patch('content_api.items.service.utcnow')
    def test_sets_end_date_and_start_date_to_today_if_both_not_given(
        self, fake_utcnow
    ):
        request = MagicMock()
        request.args = MultiDict()
        lookup = {}

        fake_utcnow.return_value.date.return_value = date(2014, 7, 15)

        instance = self._make_one()
        instance.get(request, lookup)

        self.assertTrue(fake_super_get.called)
        args, _ = fake_super_get.call_args
        self.assertGreater(len(args), 0)

        filters = json.loads(args[0].args['filter'])['bool']['must']
        date_filter = filters[0].get('range', {}).get('versioncreated', {})
        expected_filter = {
            'gte': '2014-07-08',
            'lte': '2014-07-15'
        }
        self.assertEqual(date_filter, expected_filter)

    def test_creates_correct_query_if_start_and_end_date_are_the_same(self):
        request = MagicMock()
        request.args = MultiDict([
            ('start_date', '2010-09-17'),
            ('end_date', '2010-09-17')]
        )
        lookup = {}

        instance = self._make_one()
        instance.get(request, lookup)

        self.assertTrue(fake_super_get.called)
        args, _ = fake_super_get.call_args
        self.assertGreater(len(args), 0)

        filters = json.loads(args[0].args['filter'])['bool']['must']
        date_filter = filters[0].get('range', {}).get('versioncreated', {})
        expected_filter = {
            'gte': '2010-09-17',
            'lte': '2010-09-17'
        }
        self.assertEqual(date_filter, expected_filter)

    @mock.patch('content_api.items.service.utcnow')
    def test_raises_correct_error_for_start_date_in_future(self, fake_utcnow):
        request = MagicMock()
        request.args = MultiDict([('start_date', '2007-10-31')])
        lookup = {}

        fake_utcnow.return_value.date.return_value = date(2007, 10, 30)

        from content_api.errors import BadParameterValueError
        instance = self._make_one()

        with self.assertRaises(BadParameterValueError) as context:
            instance.get(request, lookup)

        ex = context.exception
        self.assertEqual(
            ex.payload,
            "Start date (2007-10-31) must not be set in the future "
            "(current server date (UTC): 2007-10-30)"
        )

    @mock.patch('content_api.items.service.utcnow')
    def test_raises_correct_error_for_end_date_in_future(self, fake_utcnow):
        request = MagicMock()
        request.args = MultiDict([('end_date', '2007-10-31')])
        lookup = {}

        fake_utcnow.return_value.date.return_value = date(2007, 10, 30)

        from content_api.errors import BadParameterValueError
        instance = self._make_one()

        with self.assertRaises(BadParameterValueError) as context:
            instance.get(request, lookup)

        ex = context.exception
        self.assertEqual(
            ex.payload,
            "End date (2007-10-31) must not be set in the future "
            "(current server date (UTC): 2007-10-30)"
        )

    def test_raises_error_for_invalid_parameter_for_service(self):
        request = MagicMock()
        request.args = MultiDict([('service', '')])
        lookup = {}

        from content_api.errors import BadParameterValueError
        instance = self._make_one()

        with self.assertRaises(BadParameterValueError) as context:
            instance.get(request, lookup)

        ex = context.exception
        self.assertEqual(
            ex.payload,
            'Bad parameter value for Parameter ({})'.format('service')
        )

    def test_set_filter_for_service(self):
        request = MagicMock()
        request.args = MultiDict([('service', 'i')])
        lookup = {}

        instance = self._make_one()
        instance.get(request, lookup)

        self.assertTrue(fake_super_get.called)
        args, _ = fake_super_get.call_args
        self.assertGreater(len(args), 0)

        filters = json.loads(args[0].args['filter'])['bool']['must']
        self.assertEqual(filters[0], {'terms': {'service.code': ['i']}})

    def test_raises_error_for_invalid_parameter_for_urgency(self):
        request = MagicMock()
        request.args = MultiDict([('urgency', '')])
        lookup = {}

        from content_api.errors import BadParameterValueError
        instance = self._make_one()

        with self.assertRaises(BadParameterValueError) as context:
            instance.get(request, lookup)

        ex = context.exception
        self.assertEqual(
            ex.payload,
            'Bad parameter value for Parameter ({})'.format('urgency')
        )

    def test_set_filter_for_urgency(self):
        request = MagicMock()
        request.args = MultiDict([('urgency', 1)])
        lookup = {}

        instance = self._make_one()
        instance.get(request, lookup)

        self.assertTrue(fake_super_get.called)
        args, _ = fake_super_get.call_args
        self.assertGreater(len(args), 0)

        filters = json.loads(args[0].args['filter'])['bool']['must']
        self.assertEqual(filters[0], {'terms': {'urgency': [1]}})

    def test_set_filter_for_q(self):
        expected = '(foo OR bar) AND headline:test'
        request = MagicMock()
        request.args = MultiDict([('q', expected)])
        lookup = {}

        instance = self._make_one()
        instance.get(request, lookup)

        self.assertTrue(fake_super_get.called)
        args, _ = fake_super_get.call_args
        self.assertGreater(len(args), 0)

        q = args[0].args['q']
        self.assertEqual(q, expected)


class ParseIsoDateMethodTestCase(ItemsServiceTestCase):
    """Tests for the _parse_iso_date() helper method."""

    def test_returns_none_if_none_given(self):
        klass = self._get_target_class()
        result = klass._parse_iso_date(None)
        self.assertIsNone(result)

    def test_returns_date_object_on_valid_iso_date_string(self):
        klass = self._get_target_class()
        result = klass._parse_iso_date('2015-05-15')
        self.assertEqual(result, date(2015, 5, 15))

    def test_raises_value_error_on_invalid_iso_date_string(self):
        klass = self._get_target_class()
        with self.assertRaises(ValueError):
            klass._parse_iso_date('5th May 2015')


class SetFieldsFilterMethodTestCase(ItemsServiceTestCase):
    """Tests for the _set_fields_filter() helper method."""

    def test_raises_error_if_requesting_to_exclude_required_field(self):
        request = MagicMock()
        request.args = MultiDict([('exclude_fields', 'uri')])
        request.projection = None

        from content_api.errors import BadParameterValueError
        instance = self._make_one()

        with self.assertRaises(BadParameterValueError) as context:
            instance._set_fields_filter(request)

        ex = context.exception
        self.assertEqual(
            ex.payload,
            'Cannot exclude a content field required by the NINJS format '
            '(uri).'
        )

    def test_raises_error_if_field_whitelist_and_blacklist_both_given(self):
        request = MagicMock()
        request.args = MultiDict([
            ('include_fields', 'language'),
            ('exclude_fields', 'body_text'),
        ])
        request.projection = None

        from content_api.errors import UnexpectedParameterError
        instance = self._make_one()

        with self.assertRaises(UnexpectedParameterError) as context:
            instance._set_fields_filter(request)

        ex = context.exception
        self.assertEqual(
            ex.payload,
            'Cannot both include and exclude content fields at the same time.'
        )

    def test_raises_error_if_whitelisting_unknown_content_field(self):
        request = MagicMock()
        request.args = MultiDict([('include_fields', 'field_x')])
        request.projection = None

        from content_api.errors import BadParameterValueError
        from content_api.items import ItemsResource

        instance = self._make_one()

        fake_schema = {'foo': 'schema_bar'}
        with mock.patch.object(ItemsResource, 'schema', new=fake_schema):  # @UndefinedVariable
            with self.assertRaises(BadParameterValueError) as context:
                instance._set_fields_filter(request)

            ex = context.exception
            self.assertEqual(
                ex.payload, 'Unknown content field to include (field_x).')

    def test_raises_error_if_blacklisting_unknown_content_field(self):
        request = MagicMock()
        request.args = MultiDict([('exclude_fields', 'field_x')])
        request.projection = None

        from content_api.errors import BadParameterValueError
        from content_api.items import ItemsResource

        instance = self._make_one()

        fake_schema = {'foo': 'schema_bar'}
        with mock.patch.object(ItemsResource, 'schema', new=fake_schema):  # @UndefinedVariable
            with self.assertRaises(BadParameterValueError) as context:
                instance._set_fields_filter(request)

            ex = context.exception
            self.assertEqual(
                ex.payload, 'Unknown content field to exclude (field_x).')

    def test_filters_out_blacklisted_fields_if_requested(self):
        request = MagicMock()
        request.args = MultiDict([('exclude_fields', 'language,version')])
        request.projection = None

        instance = self._make_one()
        instance._set_fields_filter(request)

        projection = json.loads(request.projection) if request.projection else {}
        expected_projection = {
            'language': 0,
            'version': 0,
        }
        self.assertEqual(projection, expected_projection)

    def test_filters_out_all_but_whitelisted_fields_if_requested(self):
        request = MagicMock()
        request.args = MultiDict([('include_fields', 'body_text,byline')])
        request.projection = None

        instance = self._make_one()
        instance._set_fields_filter(request)

        projection = json.loads(request.projection) if request.projection else {}
        expected_projection = {
            'body_text': 1,
            'byline': 1,
        }
        self.assertEqual(projection, expected_projection)


fake_super_find_one = MagicMock(name='fake super().find_one')


@mock.patch('content_api.items.service.BaseService.find_one', fake_super_find_one)
class FindOneMethodTestCase(ItemsServiceTestCase):
    """Tests for the find_one() method."""

    def setUp(self):
        super().setUp()
        fake_super_find_one.reset_mock()

    @mock.patch('content_api.items.service.ItemsService._check_for_unknown_params')
    def test_correctly_invokes_parameter_validation(self, fake_check_unknown):
        fake_request = MagicMock()
        fake_request.args = MultiDict()
        lookup = {'_id': 'my_item'}

        instance = self._make_one()
        instance.find_one(fake_request, **lookup)

        self.assertTrue(fake_check_unknown.called)
        args, kwargs = fake_check_unknown.call_args

        self.assertGreater(len(args), 0)
        self.assertEqual(args[0], fake_request)
        self.assertEqual(kwargs.get('allow_filtering'), False)

        expected_whitelist = sorted(['exclude_fields', 'include_fields', 'version'])

        whitelist_arg = kwargs.get('whitelist')
        if whitelist_arg is not None:
            # NOTE: the whitelist argument is converted to a list, because any
            # iterable type is valid, not just lists
            self.assertEqual(sorted(list(whitelist_arg)), expected_whitelist)
        else:
            # whitelist can also be passed as a positional argument
            self.assertGreater(len(args), 1)
            self.assertEqual(sorted(list(args[1])), expected_whitelist)

    @mock.patch('content_api.items.service.ItemsService._set_fields_filter')
    def test_sets_fields_filter_on_request_object(self, fake_set_fields_filter):
        fake_request = MagicMock()
        fake_request.args = MultiDict()
        fake_request.projection = None
        lookup = {}

        instance = self._make_one()
        instance.find_one(fake_request, **lookup)

        self.assertTrue(fake_set_fields_filter.called)
        args, _ = fake_set_fields_filter.call_args

        self.assertGreater(len(args), 0)
        self.assertIs(args[0], fake_request)

    def test_invokes_superclass_method_with_given_arguments(self):
        request = MagicMock()
        request.args = MultiDict()
        lookup = {'_id': 'my_item'}

        instance = self._make_one()
        instance.find_one(request, **lookup)

        self.assertTrue(fake_super_find_one.called)
        args, kwargs = fake_super_find_one.call_args
        self.assertEqual(len(args), 1)
        self.assertIs(args[0], request)
        self.assertEqual(kwargs['_id'], lookup['_id'])

    def test_provides_request_object_to_superclass_if_not_given(self):
        lookup = {'_id': 'my_item'}

        instance = self._make_one()
        instance.find_one(None, **lookup)

        self.assertTrue(fake_super_find_one.called)
        args, _ = fake_super_find_one.call_args
        self.assertEqual(len(args), 1)
        self.assertIsInstance(args[0], ParsedRequest)


class OnFetchedItemMethodTestCase(ItemsServiceTestCase):
    """Tests for the on_fetched_item() method."""

    def setUp(self):
        super().setUp()

        self.app = Flask(__name__)
        self.app.config['CONTENTAPI_URL'] = 'http://content_api.com'
        self.app.config['URLS'] = {'items': 'items_endpoint'}

        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()
        super().tearDown()

    def test_sets_uri_field_on_fetched_document(self):
        document = {
            '_id': 'item:123',
            'headline': 'a test item'
        }

        instance = self._make_one(datasource='items')
        instance.on_fetched_item(document)

        self.assertEqual(
            document.get('uri'),
            'http://content_api.com/items_endpoint/item%3A123'  # %3A == urlquote(':')
        )

    def test_removes_non_ninjs_content_fields_from_fetched_document(self):
        document = {
            '_id': 'item:123',
            '_etag': '12345abcde',
            '_created': '12345abcde',
            '_updated': '12345abcde',
            'headline': 'breaking news',
            'ancestors': ['item:1234'],
            'subscribers': [],
            '_current_version': '1',
            '_latest_version': '1'
        }

        instance = self._make_one(datasource='items')
        instance.on_fetched_item(document)

        for field in ('_created', '_etag', '_id', '_updated', 'ancestors',
                      'subscribers', '_current_version', '_latest_version'):
            self.assertNotIn(field, document)

    def test_does_not_remove_hateoas_links_from_fetched_document(self):
        document = {
            '_id': 'item:123',
            'headline': 'breaking news',
            '_links': {
                'self': {
                    'href': 'link/to/item/itself',
                    'title': 'Item'
                }
            }
        }

        instance = self._make_one(datasource='items')
        instance.on_fetched_item(document)

        expected_links = {
            'self': {'href': 'link/to/item/itself', 'title': 'Item'}
        }
        self.assertEqual(document.get('_links'), expected_links)


class OnFetchedMethodTestCase(ItemsServiceTestCase):
    """Tests for the on_fetched() method."""

    def setUp(self):
        super().setUp()

        self.app = Flask(__name__)
        self.app.config['CONTENTAPI_URL'] = 'http://content_api.com'
        self.app.config['URLS'] = {'items': 'items_endpoint'}

        self.app_context = self.app.app_context()
        self.app_context.push()
        self.req_context = self.app.test_request_context('items/')
        self.req_context.push()

    def tearDown(self):
        self.req_context.pop()
        self.app_context.pop()
        super().tearDown()

    def test_sets_uri_field_on_all_fetched_documents(self):
        result = {
            '_items': [
                {'_id': 'item:123', 'headline': 'a test item'},
                {'_id': 'item:555', 'headline': 'another item'},
            ]
        }

        instance = self._make_one(datasource='items')
        instance.on_fetched(result)

        documents = result['_items']
        self.assertEqual(
            documents[0].get('uri'),
            'http://content_api.com/items_endpoint/item%3A123'  # %3A == urlquote(':')
        )
        self.assertEqual(
            documents[1].get('uri'),
            'http://content_api.com/items_endpoint/item%3A555'  # %3A == urlquote(':')
        )

    def test_removes_non_ninjs_content_fields_from_all_fetched_documents(self):
        result = {
            '_items': [{
                '_id': 'item:123',
                '_etag': '12345abcde',
                '_created': '12345abcde',
                '_updated': '12345abcde',
                'headline': 'breaking news',
                'ancestors': ['item:1234'],
                'subscribers': [],
                '_current_version': '1',
                '_latest_version': '1'
            }, {
                '_id': 'item:555',
                '_etag': '67890fedcb',
                '_created': '2121abab',
                '_updated': '2121abab',
                'headline': 'good news',
                'ancestors': ['item:5554'],
                'subscribers': [],
                '_current_version': '1',
                '_latest_version': '1'
            }]
        }

        instance = self._make_one(datasource='items')
        instance.on_fetched(result)

        documents = result['_items']
        for doc in documents:
            for field in ('_created', '_etag', '_id', '_updated', 'ancestors',
                          'subscribers', '_current_version', '_latest_version'):
                self.assertNotIn(field, doc)

    def test_does_not_remove_hateoas_links_from_fetched_documents(self):
        result = {
            '_items': [{
                '_id': 'item:123',
                '_etag': '12345abcde',
                '_created': '12345abcde',
                '_updated': '12345abcde',
                'headline': 'breaking news',
                '_links': {
                    'self': {
                        'href': 'link/to/item_123',
                        'title': 'Item'
                    }
                }
            }, {
                '_id': 'item:555',
                '_etag': '67890fedcb',
                '_created': '2121abab',
                '_updated': '2121abab',
                'headline': 'good news',
                '_links': {
                    'self': {
                        'href': 'link/to/item_555',
                        'title': 'Item'
                    }
                }
            }]
        }

        instance = self._make_one(datasource='items')
        instance.on_fetched(result)

        documents = result['_items']

        expected_links = {
            'self': {'href': 'link/to/item_123', 'title': 'Item'}
        }
        self.assertEqual(documents[0].get('_links'), expected_links)

        expected_links = {
            'self': {'href': 'link/to/item_555', 'title': 'Item'}
        }
        self.assertEqual(documents[1].get('_links'), expected_links)

    def test_sets_collection_self_link_to_relative_original_url(self):
        result = {
            '_items': [],
            '_links': {
                'self': {'href': 'foo/bar/baz'}
            }
        }

        request_url = 'items?start_date=1975-12-31#foo'
        with self.app.test_request_context(request_url):
            instance = self._make_one(datasource='items')
            instance.on_fetched(result)

        self_link = result.get('_links', {}).get('self', {}).get('href')
        self.assertEqual(self_link, 'items?start_date=1975-12-31%23foo')

    @mock.patch('content_api.items.service.g')
    def test_removes_associated_item_if_subscriber_is_not_entitled(self, fake_g):
        fake_g.get = MagicMock(return_value='test')
        result = {
            '_items': [
                {
                    '_id': 'item:123',
                    'headline': 'a test item',
                    'associations': {
                        'featuremedia': {
                            '_id': 'a1',
                            'subscribers': ['test']
                        }
                    }
                },
                {
                    '_id': 'item:555',
                    'headline': 'another item',
                    'associations': {
                        'featuremedia': {
                            '_id': 'a2',
                            'subscribers': ['test2']
                        }
                    }
                },
            ]
        }

        with self.app.test_request_context():
            instance = self._make_one(datasource='items')
            instance.on_fetched(result)

        self.assertEqual(result['_items'][0]['associations']['featuremedia']['_id'], 'a1')
        self.assertNotIn('subscribers', result['_items'][0]['associations']['featuremedia'])
        self.assertNotIn('featuremedia', result['_items'][1]['associations'])


class GetUriMethodTestCase(ItemsServiceTestCase):
    """Tests for the _get_uri() helper method."""

    def setUp(self):
        super().setUp()

        self.app = Flask(__name__)
        self.app.config['CONTENTAPI_URL'] = 'http://content_api.com'
        self.app.config['URLS'] = {
            'items': 'items_endpoint',
            'packages': 'packages_endpoint'
        }

        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()
        super().tearDown()

    def test_generates_correct_uri_for_non_composite_items(self):
        document = {
            '_id': 'foo:bar',
            'type': 'picture'
        }

        instance = self._make_one(datasource='items')
        result = instance._get_uri(document)

        self.assertEqual(result, 'http://content_api.com/items_endpoint/foo%3Abar')

    def test_generates_correct_uri_for_composite_items(self):
        document = {
            '_id': 'foo:bar',
            'type': 'composite'
        }

        instance = self._make_one(datasource='items')
        result = instance._get_uri(document)

        self.assertEqual(result, 'http://content_api.com/packages_endpoint/foo%3Abar')


class GetExpiredItemsTestCase(TestCase):
    """Tests for the `get_expired_items` helper method."""

    def setUp(self):
        utc = utcnow()
        expired = utc - timedelta(days=10)
        not_expired = utc - timedelta(days=1)
        self.app.data.insert('items', [
            {'_id': 'a1', '_updated': not_expired, 'type': 'text'},  # Single item, not expired

            {'_id': 'b2', '_updated': expired, 'type': 'text'},  # Single item, expired

            # Evolved from: parent expired, child not expired
            {'_id': 'c3', '_updated': expired, 'type': 'text'},
            {'_id': 'd4', '_updated': not_expired, 'type': 'text', 'evolvedfrom': 'c3', 'ancestors': ['c3']},

            # Evolved from: parent expired, child expired
            {'_id': 'e5', '_updated': expired, 'type': 'text'},
            {'_id': 'f6', '_updated': expired, 'type': 'text', 'evolvedfrom': 'e5', 'ancestors': ['e5']},

            # Multi-branch evolved from,
            {'_id': 'g7', '_updated': expired, 'type': 'text'},
            {'_id': 'h8', '_updated': expired, 'type': 'text', 'evolvedfrom': 'g7', 'ancestors': ['g7']},
            {'_id': 'i9', '_updated': not_expired, 'type': 'text', 'evolvedfrom': 'h8', 'ancestors': ['g7', 'h8']},

            # Multi-branch evolved from
            {'_id': 'j10', '_updated': expired, 'type': 'text'},
            {'_id': 'k11', '_updated': expired, 'type': 'text', 'evolvedfrom': 'j10', 'ancestors': ['j10']},
            {'_id': 'l12', '_updated': expired, 'type': 'text', 'evolvedfrom': 'k11', 'ancestors': ['j10', 'k11']},
        ])
        self.expired_ids = ['b2', 'c3', 'e5', 'f6', 'g7', 'h8', 'j10', 'k11', 'l12']
        self.service = get_resource_service('items')

    def test_get_only_expired_items(self):
        expired_items = []
        for items in self.service.get_expired_items(expiry_days=8):
            expired_items.extend(items)

        self.assertEqual(len(expired_items), 9)

        for item in expired_items:
            self.assertIn(item['_id'], self.expired_ids)

    def test_generator_iteration(self):
        """Tests that the yield generator works for `get_expired_items`

        Ensures that each iteration contains the correct items
        """
        iterations = 0
        for items in self.service.get_expired_items(expiry_days=8, max_results=4):
            iterations += 1
            self.assertLess(iterations, 4)

            num_items = len(items)
            item_ids = [item['_id'] for item in items]

            if iterations == 1:
                self.assertEqual(num_items, 4)
                self.assertEqual(item_ids, ['b2', 'c3', 'e5', 'f6'])
            elif iterations == 2:
                self.assertEqual(num_items, 4)
                self.assertEqual(item_ids, ['g7', 'h8', 'j10', 'k11'])
            elif iterations == 3:
                self.assertEqual(num_items, 1)
                self.assertEqual(item_ids, ['l12'])

        self.assertEqual(iterations, 3)

    def test_get_expired_not_including_children(self):
        expired_items = []
        for items in self.service.get_expired_items(expiry_days=8, include_children=False):
            expired_items.extend(items)

        self.assertEqual(len(expired_items), 5)

        for item in expired_items:
            self.assertIn(item['_id'], ['b2', 'c3', 'e5', 'g7', 'j10'])
