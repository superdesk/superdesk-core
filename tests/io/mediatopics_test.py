# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import unittest

from superdesk.io.mediatopics import MediaTopicsIndex
from superdesk.io.iptc import subject_codes


class MediaTopicsTestCase(unittest.TestCase):
    def setUp(self):
        self.topics = MediaTopicsIndex()

    def test_all_subjects_map_to_a_media_topic(self):
        for (k, v) in sorted(subject_codes.items()):
            topic = self.topics.get_media_topic(k)
            self.assertIsNotNone(topic)
            # print(k, v, '\t---->\t',topic, self.topics.get_media_topic_item(topic).get('prefLabel').get('en-GB'))

    def test_get_items(self):
        items = self.topics.get_items()
        for i in items:
            subject = self.topics.get_subject_code(i.get("qcode"))
            self.assertIsNotNone(subject)
            # print(i.get('qcode'), i.get('name'), '\t---->\t', subject, subject_codes.get(subject))

    def test_get_media_topics(self):
        items = self.topics.get_media_topics()
        for (i, v) in items.items():
            subject = self.topics.get_subject_code(i)
            self.assertIsNotNone(subject)
            # print(i, v.get('prefLabel').get('en-GB'), '\t---->\t', subject, subject_codes.get(subject))

    def test_media_topic_to_subject(self):
        subject = self.topics.get_subject_code("medtop:20000070")
        self.assertEqual(subject, "16004000")

    def test_subject_to_media_topic(self):
        topic = self.topics.get_media_topic("16004000")
        self.assertEqual(topic, "medtop:20000070")

    def test_get_media_topic_item(self):
        topic = self.topics.get_media_topic_item("medtop:20000070")
        self.assertEqual(topic["type"], ["http://www.w3.org/2004/02/skos/core#Concept"])
