# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import os
from json import loads
from .subjectcodes import get_parent_subjectcode
import logging

logger = logging.getLogger(__name__)


class MediaTopicsIndex:
    def __init__(self):
        # A map for mapping from an IPTC subject code to a Media Topic
        self.subject_media_topic_map = dict()
        # A map for mapping from a Media Topic code to a subject code.
        self.media_topic_to_subject_map = dict()
        # A map that contains all the media topics.
        self.media_topic_map = dict()

        dirname = os.path.dirname(os.path.realpath(__file__))

        # The media topics json file is available at http://cv.iptc.org/newscodes/mediatopic?lang=x-all
        # there are also language specific files that could be used.
        media_topic_codes = os.path.join(dirname, "data", "cptall-x-all.json")
        mediatopics = self._load_codes(media_topic_codes)
        self.generate_mediatopic_to_subject_map(mediatopics.get("conceptSet"))

    def _load_codes(self, filename):
        with open(filename, "r", encoding="UTF-8") as f:
            return loads(f.read())

    def clear_maps(self):
        """Clear the maps to enable them to be regenerated

        :return:
        """
        self.subject_media_topic_map = dict()
        self.media_topic_to_subject_map = dict()

    def generate_mediatopic_to_subject_map(self, mediatopics):
        """Scan the the media topics and create lookup maps for mapping subject codes to media topics and
        media topics to subjects

        :param mediatopics:
        :return:
        """
        working_map = dict()

        def set_map_entry(topic, match_type):
            match_list = topic.get(match_type, [])
            if len(match_list):
                for s in match_list:
                    if s.startswith("http://cv.iptc.org/newscodes/subjectcode/"):
                        subject_qcode = s.split("/")[-1]
                        if subject_qcode not in working_map:
                            working_map[subject_qcode] = {match_type: [topic.get("qcode")]}
                        else:
                            if match_type in working_map[subject_qcode]:
                                working_map[subject_qcode][match_type].append(topic.get("qcode"))
                            else:
                                working_map[subject_qcode][match_type] = [topic.get("qcode")]
                        if topic.get("qcode") not in self.media_topic_to_subject_map:
                            self.media_topic_to_subject_map[t.get("qcode")] = subject_qcode

        # For each media topic build match lists for each of the match types
        for t in mediatopics:
            # Save each Media Topic
            self.media_topic_map[t.get("qcode")] = t

            # Extract each match list
            set_map_entry(t, "exactMatch")
            set_map_entry(t, "closeMatch")
            set_map_entry(t, "broadMatch")

        # Construct a list in order of how close the match is, in some cases there may be for example multiple exact
        # matches, in this case the first one is chosen
        for (k, v) in working_map.items():
            matches = v.get("exactMatch", []) if "exactMatch" in v else []
            matches = matches + (v.get("closeMatch", []) if "closeMatch" in v else [])
            matches = matches + (v.get("broadMatch", []) if "broadMatch" in v else [])
            self.subject_media_topic_map[k] = matches[0] if len(matches) else None

    def get_subject_code(self, qcode):
        """Given a Media Topic qcode return the corresponding subject code, if a direct match cannot be found we try the
        parents

        :param qcode:
        :return:
        """
        current_topic = qcode
        subject = self.media_topic_to_subject_map.get(qcode)
        if subject:
            return subject
        while not subject:
            parent_topic = self._get_parent(self.get_media_topic_item(current_topic))
            if not parent_topic:
                return None
            subject = self.media_topic_to_subject_map.get(parent_topic)
            if subject:
                return subject
            current_topic = parent_topic

    def get_media_topic(self, subject):
        """Given a subject code return the closest matching media topic qcode

        :param subject:
        :return:
        """
        current_subject = subject
        qcode = self.subject_media_topic_map.get(current_subject)
        if qcode:
            return qcode
        while not qcode:
            parent_subject = get_parent_subjectcode(current_subject)
            if not parent_subject:
                return None
            qcode = self.subject_media_topic_map.get(parent_subject)
            if qcode:
                return qcode
            current_subject = parent_subject

    def get_media_topic_item(self, qcode):
        """Given the qcode for a media topic return the entire structure

        :param qcode:
        :return:
        """
        return self.media_topic_map.get(qcode, None)

    def get_media_topics(self):
        return self.media_topic_map

    def _get_pref_label(self, topic, language):
        """Extract a label for the media topic in the requested language

        :param topic:
        :param language:
        :return:
        """
        label = topic.get("prefLabel").get(language)
        if not label:
            # Not all languages are fully populated, but English seems to be.
            label = topic.get("prefLabel").get("en-GB")
            if not label:
                # Just return the first available
                key = list(topic.get("prefLabel").keys())[0]
                return topic.get("prefLabel").get(key)
        return label

    def _get_parent(self, topic):
        return (
            "medtop:" + topic.get("broader")[0].split("/")[-1]
            if len(topic.get("broader", []))
            and topic.get("broader")[0].startswith("http://cv.iptc.org/newscodes/mediatopic/")
            else None
        )

    def get_items(self, language="en-GB"):
        """Get list of all subjects.

        Each topic is a dict with `qcode`, `name` and `parent` and list of 'children' keys.
        """
        items = []
        for (_k, code) in self.media_topic_map.items():
            if not code.get("retired"):
                items.append(
                    {
                        "qcode": code.get("qcode"),
                        "name": self._get_pref_label(code, language),
                        "parent": self._get_parent(code),
                        "children": code.get("narrower"),
                    }
                )
        return sorted(items, key=lambda k: k["name"])


def init_app(app):
    app.mediatopics = MediaTopicsIndex()
