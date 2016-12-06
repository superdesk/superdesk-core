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
import re
import os

from eve.utils import ParsedRequest

from apps.content_filters.filter_condition.filter_condition_service import FilterConditionService
from apps.content_filters.filter_condition.filter_condition import FilterCondition
from apps.content_filters.filter_condition.filter_condition_operator import FilterConditionOperator
from superdesk import get_resource_service
from superdesk.tests import TestCase
from superdesk.vocabularies.command import VocabulariesPopulateCommand


class FilterConditionTests(TestCase):

    def setUp(self):
        self.req = ParsedRequest()
        with self.app.test_request_context(self.app.config.get('URL_PREFIX')):
            self.articles = [{'_id': '1', 'urgency': 1, 'headline': 'story', 'state': 'fetched'},
                             {'_id': '2', 'headline': 'prtorque', 'state': 'fetched'},
                             {'_id': '3', 'urgency': 3, 'state': 'fetched', 'flags': {'marked_for_sms': True}},
                             {'_id': '4', 'urgency': 4, 'state': 'fetched', 'task': {'desk': '1'}},
                             {'_id': '5', 'urgency': 2, 'state': 'fetched', 'task': {'desk': '2'}},
                             {'_id': '6', 'state': 'fetched'},
                             {'_id': '7', 'genre': [{'name': 'Sidebar'}], 'state': 'fetched'},
                             {'_id': '8', 'subject': [{'name': 'adult education',
                                                       'qcode': '05001000',
                                                       'parent': '05000000'},
                                                      {'name': 'high schools',
                                                       'qcode': '05005003',
                                                       'parent': '05005000'}], 'state': 'fetched'},
                             {'_id': '9', 'state': 'fetched', 'anpa_category':
                                 [{'qcode': 'a', 'name': 'Aus News'}]},
                             {'_id': '10', 'body_html': '<p>Mention<p>'},
                             {'_id': '11', 'place': [{'qcode': 'NSW', 'name': 'NSW'}], 'state': 'fetched'}]

            self.app.data.insert('archive', self.articles)

            self.app.data.insert('filter_conditions',
                                 [{'_id': 1,
                                   'field': 'headline',
                                   'operator': 'like',
                                   'value': 'tor',
                                   'name': 'test-1'}])
            self.app.data.insert('filter_conditions',
                                 [{'_id': 2,
                                   'field': 'urgency',
                                   'operator': 'in',
                                   'value': '2',
                                   'name': 'test-2'}])
            self.app.data.insert('filter_conditions',
                                 [{'_id': 3,
                                   'field': 'urgency',
                                   'operator': 'in',
                                   'value': '3,4,5',
                                   'name': 'test-2'}])
            self.app.data.insert('filter_conditions',
                                 [{'_id': 4,
                                   'field': 'urgency',
                                   'operator': 'nin',
                                   'value': '1,2,3',
                                   'name': 'test-2'}])
            self.app.data.insert('filter_conditions',
                                 [{'_id': 5,
                                   'field': 'urgency',
                                   'operator': 'in',
                                   'value': '2,5',
                                   'name': 'test-2'}])
            self.app.data.insert('content_filters',
                                 [{"_id": 1,
                                   "content_filter": [{"expression": {"fc": [1]}}],
                                   "name": "soccer-only"}])

    def _setup_elastic_args(self, elastic_translation, search_type='filter'):
        if search_type == 'keyword':
            self.req.args = {'source': json.dumps({'query': {'bool': {'should': [elastic_translation]}}})}
        elif search_type == 'not':
            self.req.args = {'source': json.dumps({'query': {'bool': {'must_not': [elastic_translation]}}})}
        elif search_type == 'filter':
            self.req.args = {'source': json.dumps({'query': {
                                                   'filtered': {
                                                       'filter': {
                                                           'bool': {
                                                               'should': [elastic_translation]}}}}})}
        elif search_type == 'match':
            self.req.args = {'source': json.dumps({'query': {
                                                   'filtered': {
                                                       'query': {
                                                           'bool': {
                                                               'should': [{
                                                                   'bool': {
                                                                       'must': [elastic_translation]}}]}}}}})}

    def test_mongo_using_genre_filter_complete_string(self):
        f = FilterCondition('genre', 'in', 'Sidebar')
        query = f.get_mongo_query()
        with self.app.app_context():
            docs = get_resource_service('archive').\
                get_from_mongo(req=self.req, lookup=query)
            self.assertEqual(1, docs.count())
            self.assertEqual('7', docs[0]['_id'])

    def test_mongo_using_desk_filter_complete_string(self):
        f = FilterCondition('desk', 'in', '1')
        query = f.get_mongo_query()
        with self.app.app_context():
            docs = get_resource_service('archive').\
                get_from_mongo(req=self.req, lookup=query)
            self.assertEqual(1, docs.count())
            self.assertEqual('4', docs[0]['_id'])

    def test_mongo_using_desk_filter_nin(self):
        f = FilterCondition('desk', 'nin', '1')
        query = f.get_mongo_query()
        with self.app.app_context():
            docs = get_resource_service('archive').\
                get_from_mongo(req=self.req, lookup=query)
            self.assertEqual(10, docs.count())

    def test_mongo_using_sms_filter_with_is(self):
        f = FilterCondition('sms', 'in', 'true')
        query = f.get_mongo_query()
        with self.app.app_context():
            docs = get_resource_service('archive').\
                get_from_mongo(req=self.req, lookup=query)
            self.assertEqual(1, docs.count())

    def test_mongo_using_desk_filter_in_list(self):
        f = FilterCondition('desk', 'in', '1,2')
        query = f.get_mongo_query()
        with self.app.app_context():
            docs = get_resource_service('archive').\
                get_from_mongo(req=self.req, lookup=query)
            self.assertEqual(2, docs.count())

    def test_mongo_using_category_filter_complete_string(self):
        f = FilterCondition('anpa_category', 'in', 'a,i')
        query = f.get_mongo_query()
        with self.app.app_context():
            docs = get_resource_service('archive').\
                get_from_mongo(req=self.req, lookup=query)
            self.assertEqual(1, docs.count())
            self.assertEqual('9', docs[0]['_id'])

    def test_mongo_using_subject_filter_complete_string(self):
        f = FilterCondition('subject', 'in', '05005003')
        query = f.get_mongo_query()
        with self.app.app_context():
            docs = get_resource_service('archive').\
                get_from_mongo(req=self.req, lookup=query)
            self.assertEqual(1, docs.count())
            self.assertEqual('8', docs[0]['_id'])

    def test_mongo_using_like_filter_complete_string(self):
        f = FilterCondition('headline', 'like', 'story')
        query = f.get_mongo_query()
        with self.app.app_context():
            docs = get_resource_service('archive').\
                get_from_mongo(req=self.req, lookup=query)
            self.assertEqual(1, docs.count())
            self.assertEqual('1', docs[0]['_id'])

    def test_mongo_using_like_filter_partial_string(self):
        f = FilterCondition('headline', 'like', 'tor')
        query = f.get_mongo_query()
        with self.app.app_context():
            docs = get_resource_service('archive').\
                get_from_mongo(req=self.req, lookup=query)
            doc_ids = [d['_id'] for d in docs]
            self.assertEqual(2, docs.count())
            self.assertTrue('1' in doc_ids)
            self.assertTrue('2' in doc_ids)

    def test_mongo_using_startswith_filter(self):
        f = FilterCondition('headline', 'startswith', 'Sto')
        query = f.get_mongo_query()
        with self.app.app_context():
            docs = get_resource_service('archive').\
                get_from_mongo(req=self.req, lookup=query)
            self.assertEqual(1, docs.count())
            self.assertEqual('1', docs[0]['_id'])

    def test_mongo_using_endswith_filter(self):
        f = FilterCondition('headline', 'endswith', 'Que')
        query = f.get_mongo_query()
        with self.app.app_context():
            docs = get_resource_service('archive').\
                get_from_mongo(req=self.req, lookup=query)
            self.assertEqual(1, docs.count())
            self.assertEqual('2', docs[0]['_id'])

    def test_mongo_using_notlike_filter(self):
        f = FilterCondition('headline', 'notlike', 'Que')
        query = f.get_mongo_query()
        with self.app.app_context():
            docs = get_resource_service('archive').\
                get_from_mongo(req=self.req, lookup=query)
            self.assertEqual(10, docs.count())
            doc_ids = [d['_id'] for d in docs]
            self.assertTrue('2' not in doc_ids)

    def test_mongo_using_in_filter(self):
        f = FilterCondition('urgency', 'in', '3,4')
        query = f.get_mongo_query()
        with self.app.app_context():
            docs = get_resource_service('archive').\
                get_from_mongo(req=self.req, lookup=query)
            self.assertEqual(2, docs.count())
            self.assertEqual('3', docs[0]['_id'])
            self.assertEqual('4', docs[1]['_id'])

    def test_mongo_using_notin_filter(self):
        f = FilterCondition('urgency', 'nin', '2,3,4')
        query = f.get_mongo_query()
        with self.app.app_context():
            docs = get_resource_service('archive').\
                get_from_mongo(req=self.req, lookup=query)
            self.assertEqual(8, docs.count())
            doc_ids = [d['_id'] for d in docs]
            self.assertTrue('1' in doc_ids)
            self.assertTrue('2' in doc_ids)

    def test_elastic_using_genre_filter_complete_string(self):
        f = FilterCondition('genre', 'in', 'Sidebar')
        query = f.get_elastic_query()
        with self.app.app_context():
            self._setup_elastic_args(query)
            docs = get_resource_service('archive').get(req=self.req, lookup=None)
            doc_ids = [d['_id'] for d in docs]
            self.assertEqual(1, docs.count())
            self.assertTrue('7' in doc_ids)

    def test_elastic_using_sms_filter(self):
        f = FilterCondition('sms', 'in', 'true')
        query = f.get_elastic_query()
        with self.app.app_context():
            self._setup_elastic_args(query)
            docs = get_resource_service('archive').get(req=self.req, lookup=None)
            doc_ids = [d['_id'] for d in docs]
            self.assertEqual(1, docs.count())
            self.assertTrue('3' in doc_ids)

    def test_elastic_using_subject_filter_complete_string(self):
        f = FilterCondition('subject', 'in', '05005003')
        query = f.get_elastic_query()
        with self.app.app_context():
            self._setup_elastic_args(query)
            docs = get_resource_service('archive').get(req=self.req, lookup=None)
            doc_ids = [d['_id'] for d in docs]
            self.assertEqual(1, docs.count())
            self.assertTrue('8' in doc_ids)

    def test_elastic_using_anpa_category_filter_complete_string(self):
        f = FilterCondition('anpa_category', 'in', 'a,i')
        query = f.get_elastic_query()
        with self.app.app_context():
            self._setup_elastic_args(query)
            docs = get_resource_service('archive').get(req=self.req, lookup=None)
            doc_ids = [d['_id'] for d in docs]
            self.assertEqual(1, docs.count())
            self.assertTrue('9' in doc_ids)

    def test_elastic_using_in_filter(self):
        f = FilterCondition('urgency', 'in', '3,4')
        query = f.get_elastic_query()
        with self.app.app_context():
            self._setup_elastic_args(query)
            docs = get_resource_service('archive').get(req=self.req, lookup=None)
            doc_ids = [d['_id'] for d in docs]
            self.assertEqual(2, docs.count())
            self.assertTrue('4' in doc_ids)
            self.assertTrue('3' in doc_ids)

    def test_elastic_using_nin_filter(self):
        f = FilterCondition('urgency', 'nin', '3,4')
        query = f.get_elastic_query()
        with self.app.app_context():
            self._setup_elastic_args(query, 'not')
            docs = get_resource_service('archive').get(req=self.req, lookup=None)
            self.assertEqual(8, docs.count())
            doc_ids = [d['_id'] for d in docs]
            self.assertTrue('6' in doc_ids)
            self.assertTrue('5' in doc_ids)

    def test_elastic_using_like_filter(self):
        f = FilterCondition('headline', 'like', 'Tor')
        query = f.get_elastic_query()
        with self.app.app_context():
            self._setup_elastic_args(query, 'keyword')
            docs = get_resource_service('archive').get(req=self.req, lookup=None)
            self.assertEqual(2, docs.count())
            doc_ids = [d['_id'] for d in docs]
            self.assertTrue('1' in doc_ids)
            self.assertTrue('2' in doc_ids)

    def test_elastic_using_notlike_filter(self):
        f = FilterCondition('headline', 'notlike', 'que')
        query = f.get_elastic_query()
        with self.app.app_context():
            self._setup_elastic_args(query, 'not')
            docs = get_resource_service('archive').get(req=self.req, lookup=None)
            self.assertEqual(9, docs.count())
            doc_ids = [d['_id'] for d in docs]
            self.assertTrue('2' not in doc_ids)

    def test_elastic_using_startswith_filter(self):
        f = FilterCondition('headline', 'startswith', 'Sto')
        query = f.get_elastic_query()
        with self.app.app_context():
            self._setup_elastic_args(query, 'keyword')
            docs = get_resource_service('archive').get(req=self.req, lookup=None)
            self.assertEqual(1, docs.count())
            self.assertEqual('1', docs[0]['_id'])

    def test_elastic_using_endswith_filter(self):
        f = FilterCondition('headline', 'endswith', 'Que')
        query = f.get_elastic_query()
        with self.app.app_context():
            self._setup_elastic_args(query, 'keyword')
            docs = get_resource_service('archive').get(req=self.req, lookup=None)
            self.assertEqual(1, docs.count())
            self.assertEqual('2', docs[0]['_id'])

    def test_get_mongo_operator(self):
        self.assertEqual(FilterConditionOperator.factory('in').mongo_operator, '$in')
        self.assertEqual(FilterConditionOperator.factory('nin').mongo_operator, '$nin')
        self.assertEqual(FilterConditionOperator.factory('like').mongo_operator, '$regex')
        self.assertEqual(FilterConditionOperator.factory('notlike').mongo_operator, '$not')
        self.assertEqual(FilterConditionOperator.factory('startswith').mongo_operator, '$regex')
        self.assertEqual(FilterConditionOperator.factory('endswith').mongo_operator, '$regex')

    def test_get_mongo_value(self):
        f = FilterCondition('urgency', 'in', '1,2')
        self.assertEqual(f.value.get_mongo_value(f.field), [1, 2])

        f = FilterCondition('priority', 'nin', '3')
        self.assertEqual(f.value.get_mongo_value(f.field), ['3'])

        f = FilterCondition('headline', 'like', 'test')
        self.assertEqual(f.value.get_mongo_value(f.field), re.compile('.*test.*', re.IGNORECASE))

        f = FilterCondition('headline', 'notlike', 'test')
        self.assertEqual(f.value.get_mongo_value(f.field), re.compile('.*test.*', re.IGNORECASE))

        f = FilterCondition('headline', 'startswith', 'test')
        self.assertEqual(f.value.get_mongo_value(f.field), re.compile('^test', re.IGNORECASE))

        f = FilterCondition('headline', 'endswith', 'test')
        self.assertEqual(f.value.get_mongo_value(f.field), re.compile('.*test', re.IGNORECASE))

    def test_does_match_with_like_full(self):
        f = FilterCondition('headline', 'like', 'story')
        self.assertTrue(f.does_match(self.articles[0]))
        self.assertFalse(f.does_match(self.articles[1]))
        self.assertFalse(f.does_match(self.articles[2]))
        self.assertFalse(f.does_match(self.articles[3]))
        self.assertFalse(f.does_match(self.articles[4]))
        self.assertFalse(f.does_match(self.articles[5]))

    def test_does_match_with_like_partial(self):
        f = FilterCondition('headline', 'like', 'tor')
        self.assertTrue(f.does_match(self.articles[0]))
        self.assertTrue(f.does_match(self.articles[1]))
        self.assertFalse(f.does_match(self.articles[2]))
        self.assertFalse(f.does_match(self.articles[3]))
        self.assertFalse(f.does_match(self.articles[4]))
        self.assertFalse(f.does_match(self.articles[5]))

    def test_does_match_with_startswith_filter(self):
        f = FilterCondition('headline', 'startswith', 'Sto')
        self.assertTrue(f.does_match(self.articles[0]))
        self.assertFalse(f.does_match(self.articles[1]))
        self.assertFalse(f.does_match(self.articles[2]))
        self.assertFalse(f.does_match(self.articles[3]))
        self.assertFalse(f.does_match(self.articles[4]))
        self.assertFalse(f.does_match(self.articles[5]))

    def test_does_match_with_startswith_filter_html_field(self):
        f = FilterCondition('body_html', 'startswith', 'men')
        self.assertTrue(f.does_match(self.articles[9]))

    def test_does_match_with_endswith_filter(self):
        f = FilterCondition('headline', 'endswith', 'Que')
        self.assertFalse(f.does_match(self.articles[0]))
        self.assertTrue(f.does_match(self.articles[1]))
        self.assertFalse(f.does_match(self.articles[2]))
        self.assertFalse(f.does_match(self.articles[3]))
        self.assertFalse(f.does_match(self.articles[4]))
        self.assertFalse(f.does_match(self.articles[5]))

    def test_does_match_with_notlike_filter(self):
        f = FilterCondition('headline', 'notlike', 'Que')
        self.assertTrue(f.does_match(self.articles[0]))
        self.assertFalse(f.does_match(self.articles[1]))
        self.assertTrue(f.does_match(self.articles[2]))
        self.assertTrue(f.does_match(self.articles[3]))
        self.assertTrue(f.does_match(self.articles[4]))
        self.assertTrue(f.does_match(self.articles[5]))

    def test_does_match_with_genre_filter(self):
        f = FilterCondition('genre', 'in', 'Sidebar')
        self.assertFalse(f.does_match(self.articles[0]))
        self.assertFalse(f.does_match(self.articles[1]))
        self.assertFalse(f.does_match(self.articles[2]))
        self.assertFalse(f.does_match(self.articles[3]))
        self.assertFalse(f.does_match(self.articles[4]))
        self.assertFalse(f.does_match(self.articles[5]))
        self.assertTrue(f.does_match(self.articles[6]))
        self.assertFalse(f.does_match(self.articles[7]))
        self.assertFalse(f.does_match({'genre': None}))
        self.assertTrue(f.does_match({'genre': [{'name': 'Sidebar'}]}))
        self.assertFalse(f.does_match({'genre': [{'name': 'Article'}]}))
        self.assertTrue(f.does_match({'genre': [{'name': 'Sidebar'}, {'name': 'Article'}]}))

    def test_does_match_with_category_filter(self):
        f = FilterCondition('anpa_category', 'in', 'a,i')
        self.assertFalse(f.does_match(self.articles[0]))
        self.assertFalse(f.does_match(self.articles[1]))
        self.assertFalse(f.does_match(self.articles[2]))
        self.assertFalse(f.does_match(self.articles[3]))
        self.assertFalse(f.does_match(self.articles[4]))
        self.assertFalse(f.does_match(self.articles[5]))
        self.assertFalse(f.does_match(self.articles[6]))
        self.assertFalse(f.does_match(self.articles[7]))
        self.assertTrue(f.does_match(self.articles[8]))

    def test_does_match_with_subject_filter(self):
        f = FilterCondition('subject', 'in', '05005003')
        self.assertFalse(f.does_match(self.articles[0]))
        self.assertFalse(f.does_match(self.articles[1]))
        self.assertFalse(f.does_match(self.articles[2]))
        self.assertFalse(f.does_match(self.articles[3]))
        self.assertFalse(f.does_match(self.articles[4]))
        self.assertFalse(f.does_match(self.articles[5]))
        self.assertFalse(f.does_match(self.articles[6]))
        self.assertTrue(f.does_match(self.articles[7]))

    def test_does_match_with_sms_filter(self):
        f = FilterCondition('sms', 'nin', 'true')
        self.assertTrue(f.does_match(self.articles[0]))
        self.assertTrue(f.does_match(self.articles[1]))
        self.assertFalse(f.does_match(self.articles[2]))
        self.assertTrue(f.does_match(self.articles[3]))
        self.assertTrue(f.does_match(self.articles[4]))
        self.assertTrue(f.does_match(self.articles[5]))
        self.assertTrue(f.does_match(self.articles[6]))
        self.assertTrue(f.does_match(self.articles[7]))

    def test_does_match_with_in_filter(self):
        f = FilterCondition('urgency', 'in', '3,4')
        self.assertFalse(f.does_match(self.articles[0]))
        self.assertFalse(f.does_match(self.articles[1]))
        self.assertTrue(f.does_match(self.articles[2]))
        self.assertTrue(f.does_match(self.articles[3]))
        self.assertFalse(f.does_match(self.articles[4]))
        self.assertFalse(f.does_match(self.articles[5]))

    def test_does_match_with_in_filter_case_insensitive(self):
        f = FilterCondition('source', 'in', 'aap,reuters')
        self.assertTrue(f.does_match({'source': 'AAP'}))
        self.assertTrue(f.does_match({'source': 'aap'}))
        self.assertTrue(f.does_match({'source': 'REUTERS'}))
        f = FilterCondition('source', 'in', 'AAP')
        self.assertTrue(f.does_match({'source': 'AAP'}))
        self.assertTrue(f.does_match({'source': 'aap'}))
        self.assertFalse(f.does_match({'source': 'REUTERS'}))

    def test_does_match_with_nin_filter(self):
        f = FilterCondition('urgency', 'nin', '2,3,4')
        self.assertTrue(f.does_match(self.articles[0]))
        self.assertTrue(f.does_match(self.articles[1]))
        self.assertFalse(f.does_match(self.articles[2]))
        self.assertFalse(f.does_match(self.articles[3]))
        self.assertFalse(f.does_match(self.articles[4]))
        self.assertTrue(f.does_match(self.articles[5]))

    def test_are_equal1(self):
        f = FilterConditionService()
        new_doc = {'name': 'A', 'field': 'urgency', 'operator': 'nin', 'value': '2,3,4'}
        doc = {'_id': 1, 'name': 'B', 'field': 'urgency', 'operator': 'nin', 'value': '2,3,4'}
        self.assertTrue(f._are_equal(new_doc, doc))

    def test_are_equal2(self):
        f = FilterConditionService()
        new_doc = {'name': 'A', 'field': 'urgency', 'operator': 'nin', 'value': '4,2,3'}
        doc = {'_id': 1, 'name': 'B', 'field': 'urgency', 'operator': 'nin', 'value': '2,3,4'}
        self.assertTrue(f._are_equal(new_doc, doc))

    def test_are_equal3(self):
        f = FilterConditionService()
        new_doc = {'name': 'A', 'field': 'urgency', 'operator': 'nin', 'value': 'jump,track'}
        doc = {'_id': 1, 'name': 'B', 'field': 'urgency', 'operator': 'nin', 'value': 'tump,jrack'}
        self.assertTrue(f._are_equal(new_doc, doc))

    def test_are_equal4(self):
        f = FilterConditionService()
        new_doc = {'name': 'A', 'field': 'urgency', 'operator': 'nin', 'value': '4,2,3'}
        doc = {'_id': 1, 'name': 'B', 'field': 'urgency', 'operator': 'nin', 'value': '2,3'}
        self.assertFalse(f._are_equal(new_doc, doc))

    def test_if_fc_is_used(self):
        f = FilterConditionService()
        with self.app.app_context():
            self.assertTrue(f._get_referenced_filter_conditions(1).count() == 1)
            self.assertTrue(f._get_referenced_filter_conditions(2).count() == 0)

    def test_check_similar(self):
        f = get_resource_service('filter_conditions')
        filter_condition1 = {'field': 'urgency', 'operator': 'in', 'value': '2'}
        filter_condition2 = {'field': 'urgency', 'operator': 'in', 'value': '3'}
        filter_condition3 = {'field': 'urgency', 'operator': 'in', 'value': '1'}
        filter_condition4 = {'field': 'urgency', 'operator': 'in', 'value': '5'}
        filter_condition5 = {'field': 'urgency', 'operator': 'nin', 'value': '5'}
        filter_condition6 = {'field': 'headline', 'operator': 'like', 'value': 'tor'}
        with self.app.app_context():
            cmd = VocabulariesPopulateCommand()
            filename = os.path.join(os.path.abspath(
                os.path.dirname("apps/prepopulate/data_init/vocabularies.json")), "vocabularies.json")
            cmd.run(filename)
            self.assertTrue(len(f.check_similar(filter_condition1)) == 2)
            self.assertTrue(len(f.check_similar(filter_condition2)) == 1)
            self.assertTrue(len(f.check_similar(filter_condition3)) == 0)
            self.assertTrue(len(f.check_similar(filter_condition4)) == 3)
            self.assertTrue(len(f.check_similar(filter_condition5)) == 1)
            self.assertTrue(len(f.check_similar(filter_condition6)) == 1)

    def test_mongo_using_place_filter_complete_string(self):
        f = FilterCondition('place', 'in', 'NSW')
        query = f.get_mongo_query()
        with self.app.app_context():
            docs = get_resource_service('archive'). \
                get_from_mongo(req=self.req, lookup=query)
            self.assertEqual(1, docs.count())
            self.assertEqual('11', docs[0]['_id'])

    def test_elastic_using_place_filter_complete_string(self):
        f = FilterCondition('place', 'match', 'NSW')
        query = f.get_elastic_query()
        with self.app.app_context():
            self._setup_elastic_args(query, 'match')
            docs = get_resource_service('archive').get(req=self.req, lookup=None)
            doc_ids = [d['_id'] for d in docs]
            self.assertEqual(1, docs.count())
            self.assertTrue('11' in doc_ids)
