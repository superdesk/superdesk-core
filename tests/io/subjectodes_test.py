
import unittest
from datetime import datetime

from superdesk.io.subjectcodes import SubjectIndex
from superdesk.io.iptc import init_app


class SubjectcodeTestCase(unittest.TestCase):

    def setUp(self):
        self.subjects = SubjectIndex()

    def test_subjectcodes_empty(self):
        self.assertEqual([], self.subjects.get_items())

    def test_subjectcodes_register(self):
        self.subjects.register({
            '01000000': 'arts',
        }, last_modified=datetime(2015, 10, 10))

        self.assertEqual(1, len(self.subjects.get_items()))

        self.subjects.register({
            '01001000': 'archeology',
        }, last_modified=datetime(2015, 1, 1))

        self.assertEqual(2, len(self.subjects.get_items()))
        self.assertEqual(datetime(2015, 10, 10), self.subjects.last_modified)
        self.assertEqual('01000000', self.subjects.get_items()[1]['parent'])

        self.subjects.register({
            'subj:test': 'test'
        })

        self.assertEqual(3, len(self.subjects.get_items()))
        self.assertEqual(None, self.subjects.get_items()[2]['parent'])

    def test_iptc_init(self):
        init_app(self)
        self.assertEqual(1404, len(self.subjects.get_items()))
