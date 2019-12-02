# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013 - 2018 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk.io.feed_parsers.newsml_2_0 import NewsMLTwoFeedParser
from superdesk.io.registry import register_feed_parser
from superdesk.errors import ParserError
from superdesk.metadata.item import CONTENT_TYPE
from superdesk import etree as sd_etree
from superdesk import text_utils
from superdesk.utc import local_to_utc
import logging

logger = logging.getLogger(__name__)
IPTC_NS = 'http://iptc.org/std/nar/2006-10-01/'
STT_LOCATION_MAP = {
    "sttcity": {"qcode": "locality_code", "name": "locality"},
    "sttstate": {"qcode": "state_code", "name": "state"},
    "sttcountry": {"qcode": "country_code", "name": "country"},
    "wldreg": {"qcode": "world_region_code", "name": "world_region"},
}

TIMEZONE = 'Europe/Helsinki'


class STTNewsMLFeedParser(NewsMLTwoFeedParser):
    """
    Feed Parser which can parse STT variant of NewsML
    """

    NAME = 'sttnewsml'
    label = "STT NewsML"
    SUBJ_QCODE_PREFIXES = {
        'stt-subj': None,
        'sttdepartment': 'sttdepartment',
        'sttsubj': 'sttsubj',
        'sttdone1': 'sttdone1',
    }

    def can_parse(self, xml):
        return xml.tag.endswith('newsItem')

    def parse(self, xml, provider=None):
        self.root = xml
        try:
            item = self.parse_item(xml)
            if not item.get('headline'):
                item['headline'] = text_utils.get_text(item.get('body_html', '') or '', 'html')[:100]

            self.parse_version_dates(xml, item)

            # abstract
            try:
                abstract = xml.xpath("//iptc:description[@role='drol:summary']", namespaces={'iptc': IPTC_NS})[0].text
            except IndexError:
                pass
            else:
                if abstract:
                    item['abstract'] = abstract

            # genre
            for genre_elt in xml.xpath("//iptc:genre", namespaces={'iptc': IPTC_NS}):
                qcode = genre_elt.get('qcode')
                if qcode is None:
                    continue
                elif qcode.startswith('sttgenre:'):
                    qcode = qcode[9:]
                    genre_data = {'qcode': qcode}
                    name_elt = genre_elt.find(self.qname('name'))
                    name = name_elt.text if name_elt is not None and name_elt.text else ""
                    try:
                        name = self.getVocabulary("genre", qcode, name)
                    except ValueError:
                        continue
                    else:
                        genre_data['name'] = name
                        item.setdefault('genre', []).append(genre_data)
                elif qcode.startswith('sttversion:'):
                    qcode = qcode[11:]
                    version_data = {'qcode': qcode, 'scheme': 'sttversion'}
                    name_elt = genre_elt.find(self.qname('name'))
                    name = name_elt.text if name_elt is not None and name_elt.text else ""
                    try:
                        name = self.getVocabulary("sttgenre", qcode, name)
                    except ValueError:
                        continue
                    else:
                        version_data['name'] = name
                        item.setdefault('subject', []).append(version_data)

            # location
            for location_elt in xml.xpath("//iptc:assert", namespaces={'iptc': IPTC_NS}):
                qcode = location_elt.get("qcode")
                if not qcode or not qcode.startswith("sttlocmeta:"):
                    continue
                qcode = qcode.split(':')[-1]
                location_data = {"scheme": "sttlocmeta", "qcode": qcode}
                location_name = location_elt.find(self.qname('name'))
                if location_name is not None:
                    location_data['name'] = location_name.text
                for broader_elt in location_elt.xpath(".//iptc:broader[@type='cpnat:geoArea']",
                                                      namespaces={'iptc': IPTC_NS}):
                    qcode = broader_elt.get('qcode')
                    if not qcode:
                        continue
                    for key, mapping in STT_LOCATION_MAP.items():
                        if qcode.startswith(key + ":"):
                            if "qcode" in mapping:
                                qcode = qcode[len(key) + 1:]
                            try:
                                name = broader_elt.find(self.qname('name')).text
                            except AttributeError:
                                name = ""
                            try:
                                name = self.getVocabulary(key, qcode, name)
                            except ValueError:
                                continue
                            else:
                                location_data[mapping["qcode"]] = qcode
                                if "name" in mapping:
                                    location_data[mapping["name"]] = name
                item.setdefault('place', []).append(location_data)

            # public editorial note
            if 'ednote' in item:
                # stt has specific roles for public and private editorial notes
                # so we remove ednote found by parent parser, as it takes first one
                # as a public note
                del item['ednote']
            try:
                ednote = xml.xpath("//iptc:edNote[@role='sttnote:public']", namespaces={'iptc': IPTC_NS})[0].text
            except IndexError:
                pass
            else:
                if ednote:
                    item['ednote'] = ednote

            # private editorial note
            try:
                private_note = xml.xpath("//iptc:edNote[@role='sttnote:private']", namespaces={'iptc': IPTC_NS})[0].text
            except IndexError:
                pass
            else:
                if private_note:
                    item.setdefault('extra', {})['sttnote_private'] = private_note

            return [item]
        except Exception as ex:
            raise ParserError.newsmlTwoParserError(ex, provider)

    def parse_inline_content(self, tree, item):
        html_elt = tree.find(self.qname('html'))
        body_elt = html_elt.find(self.qname('body'))
        body_elt = sd_etree.clean_html(body_elt)

        content = dict()
        content['contenttype'] = tree.attrib['contenttype']
        if len(body_elt) > 0:
            contents = [sd_etree.to_string(e, encoding='unicode', method="html") for e in body_elt]
            content['content'] = '\n'.join(contents)
        elif body_elt.text:
            content['content'] = '<pre>' + body_elt.text + '</pre>'
            content['format'] = CONTENT_TYPE.PREFORMATTED

        if content.get('content'):
            content['content'] = content['content'].replace('&lt;endash&gt;-&lt;/endash&gt;', '-')

        return content

    def datetime(self, value):
        """When there is no timezone info, assume it's Helsinki timezone."""
        parsed = super().datetime(value)
        if '+' not in value:
            return local_to_utc(TIMEZONE, parsed)
        return parsed

    def parse_content_meta(self, tree, item):
        meta = super().parse_content_meta(tree, item)
        creditline = meta.find(self.qname('creditline'))
        if creditline is not None:
            item['source'] = creditline.text.replace('–', '-').rstrip('-')  # replace endash with dash

    def parse_version_dates(self, tree, item):
        """
        Uses contentModified field if exists to set versioncreated for item
        If not it uses to versioncreated
        https://dev.sourcefabric.org/browse/STTNHUB-84
        """

        meta = tree.find(self.qname('contentMeta'))

        content_updated = meta.find(self.qname('contentModified'))
        if content_updated is not None and content_updated.text:
            item['versioncreated'] = self.datetime(content_updated.text)

        content_created = meta.find(self.qname('contentCreated'))
        if content_created is not None and content_created.text and not item.get('versioncreated'):
            item['versioncreated'] = self.datetime(content_created.text)

        if not item.get('versioncreated'):
            raise Exception('contentModified and contentCreated fields are empty in ingest file')

        item.setdefault('firstpublished', item.get('versioncreated'))


register_feed_parser(STTNewsMLFeedParser.NAME, STTNewsMLFeedParser())
