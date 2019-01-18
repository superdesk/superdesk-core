# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.appendsourcefabric.org/superdesk/license

import datetime

from superdesk.io.feed_parsers.newsml_1_2 import NewsMLOneFeedParser
from superdesk.io.registry import register_feed_parser
from superdesk.errors import ParserError
from superdesk.etree import etree

class BelgaNewsMLOneFeedParser(NewsMLOneFeedParser):
    """
    Feed Parser which can parse if the feed is in NewsML 1.2 format.
    """
    NAME = 'belganewsml12'

    label = 'Belga News ML 1.2 Parser'

    def can_parse(self, xml):
        return xml.tag == 'NewsML'

    def parse(self, xml, provider=None):
        try:
            l_item=[]
            self.root = xml

            # parser the NewsEnvelope element
            item_envelop = self.parser_newsenvelop(xml.find('NewsEnvelope'))

            # parser the NewsItem element
            l_newsitem_el = xml.findall('NewsItem')
            for newsitem_el in l_newsitem_el:
                item = item_envelop

                self.parser_newsitem(item, newsitem_el)
                l_item.append(self.populate_fields(item))
            return l_item
        except Exception as ex:
            raise ParserError.newsmlOneParserError(ex, provider)

    def parser_newsenvelop(self, envelop_el):
        if envelop_el is None:
            return {}
        item = {}
        element = envelop_el.find('TransmissionId')
        if element is not None:
            item['ingest_provider_sequence'] = element.text

        element = envelop_el.find('NewsService')
        if element is not None:
            item['service'] = element.get('FormalName', '')

        elements = envelop_el.findall('NewsProduct')
        if elements is not None:
            item['products'] = []
            for element in elements:
                item['products'].append(element.get('FormalName', ''))

        element = envelop_el.find('Priority')
        if element is not None:
            item['priority'] = element.get('FormalName', 0)
        return item

    def parser_newsitem(self, item, newsitem_el):
        # Parser Identification element
        self.parser_identification(item, newsitem_el.find('Identification'))

        self.parser_newsmanagement(item, newsitem_el.find('NewsManagement'))

        self.parser_newscomponent(item, newsitem_el.find('NewsComponent'))

    def parser_newsmanagement(self, item, manage_el):

        if manage_el is None:
            return
        element = manage_el.find('NewsItemType')
        if element is not None:
            item['item_type'] = element.get('FormalName', '')

        element = manage_el.find('FirstCreated')
        if element is not None:
            item['firstcreated'] = element.text

        element = manage_el.find('ThisRevisionCreated')
        if element is not None:
            item['versioncreated'] = element.text

        element = manage_el.find('ThisRevisionCreated')
        if element is not None:
            item['versioncreated'] = element.text

        element = manage_el.find('Status')
        if element is not None:
            item['status'] = element.get('FormalName', '')

        element = manage_el.find('Urgency')
        if element is not None:
            item['urgency'] = element.get('FormalName', '')

        # parser AssociatedWith element
        elements = manage_el.findall('AssociatedWith')
        if elements:
            item['associated_with'] = {}
            for element in elements:
                data = element.get('NewsItem', '')
                item['associated_with']['item'] = data if data else None
                data = element.get('FormalName')
                if data:
                    if 'type' in item['associated_with']:
                        item['associated_with']['type'].append(data)
                    else:
                        item['associated_with']['type'] = [data]

    def parser_newscomponent(self, item, component_el):
        if component_el is None:
            return
        newsline_el = component_el.find('NewsLines')
        if newsline_el is not None:
            element = newsline_el.find('DateLine')
            if element is not None:
                item['dateline'] = {}
                item['dateline']['text'] = element.text

            element = newsline_el.find('HeadLine')
            if element is not None:
                item['headline'] = element.text

            element = newsline_el.find('NewsLine/NewsLineType')
            if element is not None:
                item['line_type'] = element.get('FormalName', '')

            element = newsline_el.find('NewsLine/NewsLineText')
            if element is not None:
                item['line_text'] = element.text

        admin_el = component_el.find('AdministrativeMetadata')
        if admin_el is not None:
            element = admin_el.find('Provider/Party')
            if element is not None:
                item['provide_id'] = element.get('FormalName', '')

        # parser DescriptiveMetadata element
        self.parser_descriptivemetadata(item, component_el.find('DescriptiveMetadata'))

        # parser ContentItem element
        self.parser_contentitem(item, component_el.find('ContentItem'))

    def parser_descriptivemetadata(self, item, descript_el):
        if descript_el is None:
            return
        element = descript_el.find('Language')
        if element is not None:
            item['language'] = element.text

        # parser SubjectCode element
        subjects = descript_el.findall('SubjectCode/SubjectDetail')
        subjects += descript_el.findall('SubjectCode/SubjectMatter')
        subjects += descript_el.findall('SubjectCode/Subject')
        item['subject'] = self.format_subjects(subjects)

        # parser OfInterestTo element
        elements = descript_el.findall('OfInterestTo')
        if elements:
            item['OfInterestTo'] = []
            for element in elements:
                item['OfInterestTo'].append(element.get('FormalName', ''))

        element = descript_el.find('DateLineDate')
        if element is not None:
            item['dateline']['date'] = element.text

        localtion_el = descript_el.find('Location')
        if localtion_el is not None:
            elements = descript_el.findall('Property')
            for element in elements:
                if element is not None:
                    item['language'] = element.text

        keywords = descript_el.findall('Property')
        if keywords:
            item['keywords'] = self.parse_attribute_values(keywords, 'Keyword')

    def parser_contentitem(self, item, content_el):
        if content_el is None:
            return
        element = content_el.find('MediaType')
        if element is not None:
            item['media_type'] = element.get('FormalName', '')
        element = content_el.find('Format')
        if element is not None:
            item['format'] = element.get('FormalName', '')

        item['body_html'] = etree.tostring(
            content_el.find('DataContent/nitf/body/body.content'),
            encoding='unicode').replace('<body.content>', '').replace('</body.content>', '')

    def parser_identification(self, item, indent_el):
        if indent_el is None:
            return
        newsident_el = indent_el.find('NewsIdentifier')
        if newsident_el is not None:
            element = newsident_el.find('ProviderId')
            if element is not None:
                item['provide_id'] = element.text

            element = newsident_el.find('DateId')
            if element is not None:
                item['date_id'] = element.text

            element = newsident_el.find('NewsItemId')
            if element is not None:
                item['item_id'] = element.text

            element = newsident_el.find('RevisionId')
            if element is not None:
                item['version'] = element.text

            element = newsident_el.find('RevisionId')
            if element is not None:
                item['version'] = element.text

            element = newsident_el.find('PublicIdentifier')
            if element is not None:
                item['guid'] = element.text

            element = newsident_el.find('NameLabel')
            if element is not None:
                item['label'] = element.text
        return


register_feed_parser(BelgaNewsMLOneFeedParser.NAME, BelgaNewsMLOneFeedParser())
