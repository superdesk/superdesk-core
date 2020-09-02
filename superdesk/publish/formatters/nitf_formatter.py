# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import superdesk
from lxml import etree as etree
from lxml.etree import SubElement
from flask import current_app as app
from superdesk.publish.formatters import Formatter
from superdesk.errors import FormatterError
from superdesk.metadata.item import ITEM_TYPE, CONTENT_TYPE, EMBARGO, FORMAT, FORMATS
from apps.archive.common import get_utc_schedule
from superdesk.text_utils import get_text


class EraseElement(Exception):
    """Remove entirely element"""


class NITFFormatter(Formatter):
    """NITF Formatter for Superdesk

    Format items to `NITF <https://iptc.org/standards/nitf/>`_ version *3.6*.
    """

    XML_ROOT = '<?xml version="1.0"?>'
    ENCODING = 'UTF-8'

    _message_attrib = {'version': "-//IPTC//DTD NITF 3.6//EN"}

    _schema_uri = 'http://www.iptc.org/std/NITF/3.6/specification'
    _schema_ref = 'http://www.iptc.org/std/NITF/3.6/specification/nitf-3-6.xsd'
    _debug_message_extra = {
        'schemaLocation': '{} {}'.format(_schema_uri, _schema_ref)}
    NITF_COMMON_ATTR = ('id', 'class', 'style')
    NITF_CELL_ALIGN = ('align', 'char', 'charoff')
    NITF_CELL_VALIGN = ('valign',)
    NITF_ALLOWED_ATTR = {
        'p': NITF_COMMON_ATTR + ('lede', 'summary', 'optional-tex'),
        'a': NITF_COMMON_ATTR + ('href', 'name', 'rel', 'rev', 'title'),
        'br': ('id',),
        'em': NITF_COMMON_ATTR,
        'q': NITF_COMMON_ATTR,
        'hl1': NITF_COMMON_ATTR,
        'hl2': NITF_COMMON_ATTR,
        'table': NITF_COMMON_ATTR + (
            'tabletype',
            'align',
            'width',
            'cols',
            'border',
            'frame',
            'rules',
            'cellspacing',
            'cellpadding'),
        'tbody': NITF_COMMON_ATTR + NITF_CELL_ALIGN + NITF_CELL_VALIGN,
        'tr': NITF_COMMON_ATTR + NITF_CELL_ALIGN + NITF_CELL_VALIGN,
        'th': NITF_COMMON_ATTR + NITF_CELL_ALIGN + NITF_CELL_VALIGN + (
            'axis',
            'axes',
            'nowrap',
            'rowspan',
            'colspan'),
        'td': NITF_COMMON_ATTR + NITF_CELL_ALIGN + NITF_CELL_VALIGN + (
            'axis',
            'axes',
            'nowrap',
            'rowspan',
            'colspan'),
        'nitf-table': ('id',),
        'ol': NITF_COMMON_ATTR + ('seqnum',),
        'ul': NITF_COMMON_ATTR,
        'li': NITF_COMMON_ATTR,
        'dl': NITF_COMMON_ATTR,
        'dt': NITF_COMMON_ATTR,
        'dd': NITF_COMMON_ATTR,
        'bq': NITF_COMMON_ATTR + ('nowrap', 'quote-source'),
        'fn': NITF_COMMON_ATTR,
        'note': NITF_COMMON_ATTR + ('noteclass', 'type'),
        'pre': NITF_COMMON_ATTR,
        'sup': NITF_COMMON_ATTR,
        'sub': NITF_COMMON_ATTR,
        'hr': NITF_COMMON_ATTR,
    }

    NITF_ENRICHED_TEXT_PARENTS = ("a", "caption", "credit", "dd", "dt", "em", "hl1", "hl2", "lang", "li",
                                  "media-caption", "media-producer", "p", "pronounce", "q", "tagline", "td", "th")

    def __init__(self):
        Formatter.__init__(self)

        # in elements' dicts, following key can be used:
        # - 'nitf': new NITF compatible element to use (empty string to remove)
        # - 'attrib': new attribute to use (replace existing one if set)
        # - 'filter': callback to use for complex changes (root_elment and element as arguments)
        self.HTML2NITF = {
            'p': {},
            'b': {
                'nitf': 'em',
                'attrib': {'class': 'bold'}},
            'br': {'filter': self.br_filter},
            'strong': {
                'nitf': 'em',
                'attrib': {'class': 'bold'}},
            'i': {
                'nitf': 'em',
                'attrib': {'class': 'italic'}},
            'em': {
                'nitf': 'em',
                'attrib': {'class': 'italic'}},
            'u': {
                'nitf': 'em',
                'attrib': {'class': 'underscore'}},
            'strike': {'nitf': 'em'},
            'sup': {},
            'sub': {},
            'a': {},
            'img': {'nitf': ''},  # <img> use <media> in nitf, so we remove element
            'blockquote': {'nitf': 'bq'},
            'pre': {},
            'ol': {},
            'ul': {},
            'li': {},
            # FIXME: hl1 is not used here as it can only appear in <hedline>
            'h1': {'nitf': 'hl2'},
            'h2': {'nitf': 'hl2'},
            'h3': {'nitf': 'hl2'},
            'h4': {'nitf': 'hl2'},
            'h5': {'nitf': 'hl2'},
            'h6': {'nitf': 'hl2'},
            # tables
            'table': {},
            'tbody': {},
            'tr': {},
            'td': {},
            'th': {},
            'style': {'nitf': EraseElement},  # <style> may be there in case of bad paste
        }

    def format(self, article, subscriber, codes=None):
        try:
            pub_seq_num = superdesk.get_resource_service('subscribers').generate_sequence_number(subscriber)

            nitf = self.get_nitf(article, subscriber, pub_seq_num)
            return [(pub_seq_num, self.XML_ROOT + etree.tostring(
                nitf,
                pretty_print=True,
                encoding=self.ENCODING
            ).decode(self.ENCODING))]
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

        self._format_title(article, head)
        self._format_meta(article, head, destination, pub_seq_num)
        self._format_head(article, head)
        self._format_body_head(article, body_head)
        self._format_body_content(article, body_content)
        self._format_body_end(article, body_end)
        return nitf

    def _textToParent(self, parent, children, idx, text):
        """Copy Element.text to parent or sibling element

        for internal use only
        """
        # we copy text to sibling element's tail
        # or to parent text if it is the first element
        if idx > 0:
            sibling = children[idx - 1]
            sibling.tail = (sibling.tail or '') + text
        else:
            parent.text = (parent.text or '') + text

    def _parse_children(self, html_elem, root_elem, attr_remove):
        children = list(html_elem)
        idx = 0
        while idx < len(children):
            child = children[idx]
            try:
                self.html2nitf(child, root_elem=root_elem, attr_remove=attr_remove)
            except ValueError:
                # the element is unknown
                # we need to save its text and tail,
                # and put its children to parent
                grandchildren = list(child)

                if child.text:
                    self._textToParent(html_elem, children, idx, child.text)

                if child.tail:
                    # we copy tail to last grandchild tail
                    # or we append to parent/sibling if there is no grandchild
                    if grandchildren:
                        last = grandchildren[-1]
                        last.tail = (last.tail or '') + child.tail
                    else:
                        self._textToParent(html_elem, children, idx, child.tail)

                # we move elem children to parent
                for grandchild_idx, grandchild in enumerate(grandchildren):
                    insert_idx = idx + grandchild_idx
                    html_elem.insert(insert_idx, grandchild)
                    children.insert(insert_idx, grandchild)

                # and remove the element
                html_elem.remove(child)
                children.remove(child)

                # and we continue with the same index, so new children are parsed
                continue
            except EraseElement:
                # the element need to be fully erased (itself and its children)
                html_elem.remove(child)
                children.remove(child)
                continue
            idx += 1

        return html_elem

    def html2nitf(self, html_elem, root_elem=None, attr_remove=None):
        """Convert HTML elements to NITF compatible elements

        :param ET.Element: HTML to clean/transform
        :param ET.Element: None if its the root element (must be a <div>)
        :param list attr_remove: attributes to remove if present
        :return ET.Element: <div> element with NITF compliant children
        """
        if root_elem is None:
            root_elem = html_elem
            assert html_elem.tag == 'div'
            # we change children of root element in place
            return self._parse_children(html_elem, root_elem, attr_remove)

        try:
            nitf_map = self.HTML2NITF[html_elem.tag]
        except KeyError:
            raise ValueError("Unhandled HTML element")
        nitf_elem = nitf_map.get('nitf')
        if nitf_elem is not None:
            if nitf_elem == '':
                raise ValueError("Element need to be removed")
            elif nitf_elem == EraseElement:
                raise EraseElement("Element need to be erased")
            html_elem.tag = nitf_elem

        if attr_remove is not None:
            for attr in attr_remove:
                if attr in html_elem.attrib:
                    del html_elem.attrib[attr]

        html_elem.attrib.update(nitf_map.get('attrib', {}))

        if 'filter' in nitf_map:
            nitf_map['filter'](root_elem, html_elem)

        attr_allowed = self.NITF_ALLOWED_ATTR.get(html_elem.tag, ())

        for attr in list(html_elem.attrib):
            if attr not in attr_allowed:
                del html_elem.attrib[attr]

        return self._parse_children(html_elem, root_elem, attr_remove)

    def br_filter(self, root_elem, html_elem):
        parent = html_elem.find('..')
        if parent.tag not in self.NITF_ENRICHED_TEXT_PARENTS:
            raise ValueError(u"this element need to be removed")
        elif parent.tag == 'p':
            if parent[-1] == html_elem and not (html_elem.tail or '').strip():
                raise ValueError(u"this element need to be removed")

    def _format_tobject(self, article, head):
        return SubElement(head, 'tobject', {'tobject.type': 'news'})

    def _format_docdata_dateissue(self, article, docdata):
        SubElement(docdata, 'date.issue', {'norm': str(article.get('firstcreated', ''))})

    def _format_docdata_doc_id(self, article, docdata):
        SubElement(docdata, 'doc-id', attrib={'id-string': article.get('guid', '')})

    def _format_docdata(self, article, docdata):
        SubElement(docdata, 'urgency', {'ed-urg': str(article.get('urgency', ''))})
        self._format_docdata_dateissue(article, docdata)
        self._format_docdata_doc_id(article, docdata)

        # ednote can exist and be set to None, that why we can't use default
        # value for article.get
        SubElement(docdata, 'ed-msg', {'info': article.get('ednote') or ''})

    def _format_pubdata(self, article, head):
        pass

    def _format_title(self, article, head):
        title = SubElement(head, 'title')
        title.text = article.get('headline', '')

    def _format_date_expire(self, article, docdata):
        if article.get(EMBARGO):
            docdata.attrib['management-status'] = 'embargoed'
            SubElement(docdata, 'date.expire',
                       {'norm': str(get_utc_schedule(article, EMBARGO).isoformat())})
        else:
            docdata.attrib['management-status'] = article.get('pubstatus', '')
            SubElement(docdata, 'date.expire', {'norm': str(article.get('expiry', ''))})

    def _format_head(self, article, head):
        tobject = self._format_tobject(article, head)
        if article.get('genre'):
            SubElement(tobject, 'tobject.property', {'tobject.property.type': article['genre'][0]['name']})
        self._format_subjects(article, tobject)

        docdata = SubElement(head, 'docdata')
        self._format_date_expire(article, docdata)
        self._format_docdata(article, docdata)
        self._format_pubdata(article, head)
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

    def _format_body_head_distributor(self, article, body_head):
        pass

    def _format_body_head_dateline(self, article, body_head):
        if article.get('dateline', {}).get('text'):
            dateline = SubElement(body_head, 'dateline')
            dateline.text = article['dateline']['text']

    def _format_body_head(self, article, body_head):
        hedline = SubElement(body_head, 'hedline')
        hl1 = SubElement(hedline, 'hl1')
        hl1.text = article.get('headline', '')

        if article.get('byline'):
            byline = SubElement(body_head, 'byline')
            byline.text = article['byline']

        self._format_body_head_distributor(article, body_head)
        self._format_body_head_dateline(article, body_head)
        self._format_body_head_abstract(article, body_head)

        for company in article.get('company_codes', []):
            org = SubElement(body_head, 'org', attrib={'idsrc': company.get('security_exchange', ''),
                                                       'value': company.get('qcode', '')})
            org.text = company.get('name', '')

    def _format_body_content(self, article, body_content):
        if article.get(FORMAT) == FORMATS.PRESERVED:
            pre = get_text(self.append_body_footer(article))
            SubElement(body_content, 'pre').text = pre
        else:
            self.map_html_to_xml(body_content, self.append_body_footer(article))

    def _format_body_end(self, article, body_end):
        if article.get('ednote'):
            tagline = SubElement(body_end, 'tagline')
            tagline.text = article['ednote']

    def can_format(self, format_type, article):
        return format_type == 'nitf' and \
            article[ITEM_TYPE] in (CONTENT_TYPE.TEXT, CONTENT_TYPE.PREFORMATTED, CONTENT_TYPE.COMPOSITE)

    def _format_meta_priority(self, article, head):
        pass

    def _format_meta(self, article, head, destination, pub_seq_num):
        """
        Appends <meta> elements to <head>
        """
        self._format_meta_priority(article, head)
