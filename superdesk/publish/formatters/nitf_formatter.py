# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import xml.etree.ElementTree as etree
from xml.etree.ElementTree import SubElement
from flask import current_app as app
from superdesk.publish.formatters import Formatter
import superdesk
from superdesk.errors import FormatterError
from superdesk.metadata.item import ITEM_TYPE, CONTENT_TYPE, EMBARGO, FORMAT, FORMATS
from apps.archive.common import get_utc_schedule
from bs4 import BeautifulSoup


class NITFFormatter(Formatter):
    """
    NITF Formatter
    """
    XML_ROOT = '<?xml version="1.0"?>'

    _message_attrib = {'version': "-//IPTC//DTD NITF 3.6//EN"}

    _schema_uri = 'http://www.iptc.org/std/NITF/3.6/specification'
    _schema_ref = 'http://www.iptc.org/std/NITF/3.6/specification/nitf-3-6.xsd'
    _debug_message_extra = {
        'schemaLocation': '{} {}'.format(_schema_uri, _schema_ref)}

    def format(self, article, subscriber, codes=None):
        try:
            pub_seq_num = superdesk.get_resource_service('subscribers').generate_sequence_number(subscriber)

            nitf = self.get_nitf(article, subscriber, pub_seq_num)
            return [(pub_seq_num, self.XML_ROOT + etree.tostring(nitf).decode('utf-8'))]
        except Exception as ex:
            raise FormatterError.nitfFormatterError(ex, subscriber)

    def get_nitf(self, article, destination, pub_seq_num):
        if app.config.get('NITF_INCLUDE_SCHEMA', False):
            self._message_attrib.update(self._debug_message_extra)
        nitf = etree.Element("nitf", attrib=self._message_attrib)
        head = SubElement(nitf, "head")
        body = SubElement(nitf, "body")
        body_head = SubElement(body, "body.head")
        body_content = SubElement(body, "body.content")

        body_end = SubElement(body, "body.end")

        self._append_meta(article, head, destination, pub_seq_num)
        self._format_head(article, head)
        self._format_body_head(article, body_head)
        self._format_body_content(article, body_content)
        self._format_body_end(article, body_end)
        return nitf

    def _format_tobject(self, article, head):
        return SubElement(head, 'tobject', {'tobject.type': 'news'})

    def _append_docdata_dateissue(self, article, docdata):
        SubElement(docdata, 'date.issue', {'norm': str(article.get('firstcreated', ''))})

    def _format_docdata(self, article, docdata):
        SubElement(docdata, 'urgency', {'ed-urg': str(article.get('urgency', ''))})
        self._append_docdata_dateissue(article, docdata)
        SubElement(docdata, 'doc-id', attrib={'id-string': article.get('guid', '')})

        if article.get('ednote'):
            SubElement(docdata, 'ed-msg', {'info': article.get('ednote', '')})

    def _format_head(self, article, head):
        title = SubElement(head, 'title')
        title.text = article.get('headline', '')

        tobject = self._format_tobject(article, head)
        if 'genre' in article and len(article['genre']) > 0:
            SubElement(tobject, 'tobject.property', {'tobject.property.type': article['genre'][0]['name']})
        self._format_subjects(article, tobject)

        if article.get(EMBARGO):
            docdata = SubElement(head, 'docdata', {'management-status': 'embargoed'})
            SubElement(docdata, 'date.expire',
                       {'norm': str(get_utc_schedule(article, EMBARGO).isoformat())})
        else:
            docdata = SubElement(head, 'docdata', {'management-status': article.get('pubstatus', '')})
            SubElement(docdata, 'date.expire', {'norm': str(article.get('expiry', ''))})

        self._format_docdata(article, docdata)
        self._format_keywords(article, head)

    def _format_subjects(self, article, tobject):
        for subject in article.get('subject', []):
            SubElement(tobject, 'tobject.subject',
                       {'tobject.subject.refnum': subject.get('qcode', '')})

    def _format_keywords(self, article, head):
        if article.get('keywords'):
            keylist = SubElement(head, 'key-list')
            for keyword in article['keywords']:
                SubElement(keylist, 'keyword', {'key': keyword})

    def _format_body_head_abstract(self, article, body_head):
        if article.get('abstract'):
            abstract = SubElement(body_head, 'abstract')
            self.map_html_to_xml(abstract, article.get('abstract'))

    def _format_body_head(self, article, body_head):
        hedline = SubElement(body_head, 'hedline')
        hl1 = SubElement(hedline, 'hl1')
        hl1.text = article.get('headline', '')

        if article.get('byline'):
            byline = SubElement(body_head, 'byline')
            byline.text = "By " + article['byline']

        if article.get('dateline', {}).get('text'):
            dateline = SubElement(body_head, 'dateline')
            dateline.text = article['dateline']['text']

        self._format_body_head_abstract(article, body_head)

        for company in article.get('company_codes', []):
            org = SubElement(body_head, 'org', attrib={'idsrc': company.get('security_exchange', ''),
                                                       'value': company.get('qcode', '')})
            org.text = company.get('name', '')

    def _format_body_content(self, article, body_content):
        if article.get(FORMAT) == FORMATS.PRESERVED:
            soup = BeautifulSoup(self.append_body_footer(article), 'html.parser')
            SubElement(body_content, 'pre').text = soup.get_text()
        else:
            self.map_html_to_xml(body_content, self.append_body_footer(article))

    def _format_body_end(self, article, body_end):
        if article.get('ednote'):
            tagline = SubElement(body_end, 'tagline')
            tagline.text = article['ednote']

    def can_format(self, format_type, article):
        return format_type == 'nitf' and \
            article[ITEM_TYPE] in (CONTENT_TYPE.TEXT, CONTENT_TYPE.PREFORMATTED, CONTENT_TYPE.COMPOSITE)

    def _append_meta_priority(self, article, head):
        pass

    def _append_meta(self, article, head, destination, pub_seq_num):
        """
        Appends <meta> elements to <head>
        """
        if 'anpa_category' in article and article['anpa_category'] is not None and len(
                article.get('anpa_category')) > 0:
            SubElement(head, 'meta',
                       {'name': 'anpa-category', 'content': article.get('anpa_category')[0].get('qcode', '')})

        self._append_meta_priority(article, head)
