# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

"""NewsML G2 Superdesk formatter"""

import superdesk
from lxml import etree
from lxml.etree import SubElement

from superdesk import etree as sd_etree
from flask import current_app as app

from superdesk.publish.formatters import Formatter
from superdesk.metadata.item import ITEM_TYPE, CONTENT_TYPE, EMBARGO, FORMATS, FORMAT
from superdesk.utc import utcnow
from superdesk.errors import FormatterError
from superdesk.publish.formatters.nitf_formatter import NITFFormatter
from superdesk.metadata.packages import PACKAGE_TYPE, REFS, RESIDREF, ROLE, GROUPS, GROUP_ID, ID_REF
from superdesk.filemeta import get_filemeta
from apps.archive.common import ARCHIVE, get_utc_schedule

XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"


def get_newsml_provider_id():
    return app.config.get('NEWSML_PROVIDER_ID')


class NewsMLG2Formatter(Formatter):
    """NewsML G2 Formatter"""

    XML_ROOT = '<?xml version="1.0" encoding="UTF-8"?>'
    now = utcnow()
    string_now = now.strftime('%Y-%m-%dT%H:%M:%S.0000Z')

    _message_nsmap = {None: 'http://iptc.org/std/nar/2006-10-01/', 'x': 'http://www.w3.org/1999/xhtml',
                      'xsi': 'http://www.w3.org/2001/XMLSchema-instance'}

    _debug_message_extra = {'{{{}}}schemaLocation'.format(_message_nsmap['xsi']): 'http://iptc.org/std/nar/2006-10-01/ \
    http://www.iptc.org/std/NewsML-G2/2.18/specification/NewsML-G2_2.18-spec-All-Power.xsd'}

    def format(self, article, subscriber, codes=None):
        """Create article in NewsML G2 format

        :param dict article:
        :param dict subscriber:
        :param list codes: selector codes
        :return [(int, str)]: return a List of tuples. A tuple consist of
            publish sequence number and formatted article string.
        :raises FormatterError: if the formatter fails to format an article
        """
        try:
            pub_seq_num = superdesk.get_resource_service('subscribers').generate_sequence_number(subscriber)
            is_package = self._is_package(article)
            news_message = etree.Element('newsMessage', attrib=self._debug_message_extra, nsmap=self._message_nsmap)
            self._format_header(article, news_message, pub_seq_num)
            item_set = self._format_item(news_message)
            if is_package:
                item = self._format_item_set(article, item_set, 'packageItem')
                self._format_groupset(article, item)
            elif article[ITEM_TYPE] in {CONTENT_TYPE.PICTURE, CONTENT_TYPE.AUDIO, CONTENT_TYPE.VIDEO}:
                item = self._format_item_set(article, item_set, 'newsItem')
                self._format_contentset(article, item)
            else:
                nitfFormater = NITFFormatter()
                nitf = nitfFormater.get_nitf(article, subscriber, pub_seq_num)
                newsItem = self._format_item_set(article, item_set, 'newsItem')
                self._format_content(article, newsItem, nitf)

            sd_etree.fix_html_void_elements(news_message)
            return [(pub_seq_num, self.XML_ROOT + etree.tostring(news_message).decode('utf-8'))]
        except Exception as ex:
            raise FormatterError.newmsmlG2FormatterError(ex, subscriber)

    def _is_package(self, article):
        """Given an article returns if it is a none takes package or not

        :param artcile:
        :return: True is package
        """
        return article[ITEM_TYPE] == CONTENT_TYPE.COMPOSITE and article.get(PACKAGE_TYPE, '') == ''

    def _format_header(self, article, news_message, pub_seq_num):
        """Creates the header element of the newsMessage.

        :param dict article:
        :param Element news_message:
        :param int pub_seq_num:
        """
        header = SubElement(news_message, 'header')
        SubElement(header, 'sent').text = self.string_now
        SubElement(header, 'sender').text = get_newsml_provider_id()
        SubElement(header, 'transmitId').text = str(pub_seq_num)
        SubElement(header, 'priority').text = str(article.get('priority', 5))
        SubElement(header, 'origin').text = article.get('original_source', article.get('source', ''))

    def _format_item(self, news_message):
        return SubElement(news_message, 'itemSet')

    def _format_item_set(self, article, item_set, item_type):
        """Construct the item element (newsItem or packageItem) and append the item_meta and contentMeta entities

        :param dict article:
        :param element item_set:
        :param str item_type:
        """
        item = SubElement(item_set, item_type, attrib={'standard': 'NewsML-G2', 'standardversion': '2.18',
                                                       'guid': article['guid'],
                                                       'version': str(article[superdesk.config.VERSION]),
                                                       XML_LANG: article.get('language', 'en'),
                                                       'conformance': 'power'})
        SubElement(item, 'catalogRef',
                   attrib={'href': 'http://www.iptc.org/std/catalog/catalog.IPTC-G2-Standards_25.xml'})
        self._format_rights(item, article)
        item_meta = SubElement(item, 'itemMeta')
        self._format_itemClass(article, item_meta)
        self._format_provider(item_meta)
        self._format_versioncreated(article, item_meta)
        self._format_firstcreated(article, item_meta)
        self._format_pubstatus(article, item_meta)

        if article.get(EMBARGO):
            SubElement(item_meta, 'embargoed').text = \
                get_utc_schedule(article, EMBARGO).isoformat()

        # optional properties
        self._format_ednote(article, item_meta)
        self._format_signal(article, item_meta)

        content_meta = SubElement(item, 'contentMeta')
        SubElement(content_meta, 'urgency').text = str(article.get('urgency', 5))
        self._format_timestamps(article, content_meta)
        self._format_creator(article, content_meta)
        self._format_located(article, content_meta)
        self._format_subject(article, content_meta)
        self._format_genre(article, content_meta)
        self._format_slugline(article, content_meta)
        self._format_headline(article, content_meta)
        self._format_place(article, content_meta)
        self._format_category(article, content_meta)
        self._format_company_codes(article, content_meta, item)

        if article[ITEM_TYPE] in {CONTENT_TYPE.PICTURE, CONTENT_TYPE.AUDIO, CONTENT_TYPE.VIDEO}:
            self._format_description(article, content_meta)
            self._format_creditline(article, content_meta)
        return item

    def _format_content(self, article, news_item, nitf):
        """Adds the content set to the xml

        :param dict article:
        :param Element newsItem:
        :param Element nitf:
        """
        content_set = SubElement(news_item, 'contentSet')
        if article.get(FORMAT) == FORMATS.PRESERVED:
            inline_data = sd_etree.get_text(self.append_body_footer(article))
            SubElement(content_set, 'inlineData',
                       attrib={'contenttype': 'text/plain'}).text = inline_data
        elif article[ITEM_TYPE] in [CONTENT_TYPE.TEXT, CONTENT_TYPE.COMPOSITE]:
            inline = SubElement(content_set, 'inlineXML',
                                attrib={'contenttype': 'application/nitf+xml'})
            inline.append(nitf)

    def _format_rights(self, newsItem, article):
        """Adds the rightsholder section to the newsItem

        :param Element newsItem:
        :param dict article:
        """
        rights = superdesk.get_resource_service('vocabularies').get_rightsinfo(article)
        rightsinfo = SubElement(newsItem, 'rightsInfo')
        holder = SubElement(rightsinfo, 'copyrightHolder')
        SubElement(holder, 'name').text = rights['copyrightholder']
        SubElement(rightsinfo, 'copyrightNotice').text = rights['copyrightnotice']
        SubElement(rightsinfo, 'usageTerms').text = rights['usageterms']

    # itemClass elements
    def _format_itemClass(self, article, item_meta):
        """Append the item class to the item_meta data element

        :param dict article:
        :param Element item_meta:
        """
        if CONTENT_TYPE.COMPOSITE and self._is_package(article):
            SubElement(item_meta, 'itemClass', attrib={'qcode': 'ninat:composite'})
            return
        if article[ITEM_TYPE] in {CONTENT_TYPE.TEXT, CONTENT_TYPE.PREFORMATTED, CONTENT_TYPE.COMPOSITE}:
            SubElement(item_meta, 'itemClass', attrib={'qcode': 'ninat:text'})
        elif article[ITEM_TYPE] in {CONTENT_TYPE.PICTURE, CONTENT_TYPE.AUDIO, CONTENT_TYPE.VIDEO}:
            SubElement(item_meta, 'itemClass', attrib={'qcode': 'ninat:%s' % article[ITEM_TYPE].lower()})

    def _format_provider(self, item_meta):
        """Appends the provider element to the item_meta element

        :param dict article:
        :param Element item_meta:
        """
        provider = SubElement(item_meta, 'provider')
        SubElement(provider, 'name').text = get_newsml_provider_id()

    def _format_versioncreated(self, article, item_meta):
        """Appends the versionCreated element to the item_meta element.

        :param dict article:
        :param Element item_meta:
        """
        SubElement(item_meta, 'versionCreated').text = article['versioncreated'].strftime('%Y-%m-%dT%H:%M:%S+00:00')

    def _format_firstcreated(self, article, item_meta):
        """Appends the firstCreated element to the item_meta element.

        :param dict article:
        :param Element item_meta:
        """
        SubElement(item_meta, 'firstCreated').text = article['firstcreated'].strftime('%Y-%m-%dT%H:%M:%S+00:00')

    def _format_pubstatus(self, article, item_meta):
        """Appends the pubStatus element to the item_meta element.

        :param dict article:
        :param Element item_meta:
        """
        SubElement(item_meta, 'pubStatus', attrib={'qcode': 'stat:' + article.get('pubstatus', 'usable')})

    def _format_signal(self, article, item_meta):
        """Appends the signal element to the item_meta element.

        :param dict article:
        :param Element item_meta:
        """
        if article['state'] == 'Corrected':
            SubElement(item_meta, 'signal', attrib={'qcode': 'sig:correction'})
        else:
            SubElement(item_meta, 'signal', attrib={'qcode': 'sig:update'})

    def _format_ednote(self, article, item_meta):
        """Appends the edNote element to the item_meta element.

        :param dict article:
        :param Element item_meta:
        """
        if 'ednote' in article and article.get('ednote', '') != '':
            SubElement(item_meta, 'edNote').text = article.get('ednote', '')

    # contentMeta elements
    def _format_timestamps(self, article, content_meta):
        """Appends the contentCreated and contentModified element to the contentMeta element.

        :param dict article:
        :param Element content_meta:
        """
        SubElement(content_meta, 'contentCreated').text = article['firstcreated'].strftime('%Y-%m-%dT%H:%M:%S+00:00')
        SubElement(content_meta, 'contentModified').text = article['versioncreated'].strftime('%Y-%m-%dT%H:%M:%S+00:00')

    def _format_creator(self, article, content_meta):
        """Appends the creator element to the contentMeta element

        :param dict article:
        :param Element content_meta:
        """
        if 'byline' in article:
            creator = SubElement(content_meta, 'creator')
            SubElement(creator, 'name').text = article.get('byline', '') or ''

    def _format_subject(self, article, content_meta):
        """Appends the subject element to the contentMeta element

        :param dict article:
        :param Element content_meta:
        """
        if 'subject' in article and len(article['subject']) > 0:
            for s in article['subject']:
                if 'qcode' in s:
                    subj = SubElement(content_meta, 'subject',
                                      attrib={'type': 'cpnat:abstract', 'qcode': 'subj:' + s['qcode']})
                    SubElement(subj, 'name', attrib={XML_LANG: 'en'}).text = s['name']

    def _format_genre(self, article, content_meta):
        """Appends the genre element to the contentMeta element

        :param dict article:
        :param Element content_meta:
        """
        if 'genre' in article and len(article['genre']) > 0:
            for g in article['genre']:
                genre = SubElement(content_meta, 'genre')
                SubElement(genre, 'name', attrib={XML_LANG: 'en'}).text = g.get('name', '')

    def _format_category(self, article, content_meta):
        """Appends the subject element to the contentMeta element

        :param dict article:
        :param Element content_meta:
        """
        for category in article.get('anpa_category', []):
            subject = SubElement(content_meta, 'subject',
                                 attrib={'type': 'cpnat:abstract', 'qcode': 'cat:' + category['qcode']})
            SubElement(subject, 'name', attrib={XML_LANG: 'en'}).text = category.get('name', '')

    def _format_slugline(self, article, content_meta):
        """Appends the slugline element to the contentMeta element

        :param dict article:
        :param Element content_meta:
        """
        SubElement(content_meta, 'slugline').text = article.get('slugline', '')

    def _format_headline(self, article, content_meta):
        """Appends the headline element to the contentMeta element

        :param dict article:
        :param Element content_meta:
        """
        SubElement(content_meta, 'headline').text = article.get('headline', '')

    def _format_place(self, article, content_meta):
        """Appends the subject (of type geoArea) element to the contentMeta element

        :param dict article:
        :param Element content_meta:
        """
        if not article.get('place'):
            return

        for place in article.get('place', []):
            if place.get('state'):
                subject = self._create_subject_element(content_meta, place.get('state'), 'loctyp:CountryArea')
                self._create_broader_element(subject, place.get('country'), 'loctyp:Country')
                self._create_broader_element(subject, place.get('world_region'), 'loctyp:WorldArea')
            elif place.get('country'):
                subject = self._create_subject_element(content_meta, place.get('country'), 'loctyp:Country')
                self._create_broader_element(subject, place.get('world_region'), 'loctyp:WorldArea')
            elif place.get('world_region'):
                self._create_subject_element(content_meta, place.get('world_region'), 'loctyp:WorldArea')

    def _create_broader_element(self, parent, broader_name, qcode, concept_type='cpnat:abstract'):
        """Create broader element.

        :param element parent: parent element under which the broader element is created
        :param str broader_name: value for the name element
        :param str qcode:
        :param str concept_type:
        """
        if broader_name:
            broader_elm = SubElement(parent, 'broader',
                                     attrib={'type': concept_type, 'qcode': qcode})
            SubElement(broader_elm, 'name').text = broader_name

    def _create_subject_element(self, parent, subject_name, qcode, concept_type='cpnat:abstract'):
        """Create a subject element

        :param element parent:
        :param str subject_name: value for the name element
        :param str qcode:
        :param str concept_type:
        :return: returns the subject element.
        """
        subject_elm = SubElement(parent, 'subject',
                                 attrib={'type': concept_type, 'qcode': qcode})
        SubElement(subject_elm, 'name').text = subject_name
        return subject_elm

    def _format_located(self, article, content_meta):
        """Appends the located element to the contentMeta element

        :param dict article:
        :param Element content_meta:
        """
        located = article.get('dateline', {}).get('located', {})
        if located and located.get('city'):
            located_elm = SubElement(content_meta, 'located',
                                     attrib={'type': 'cpnat:abstract', 'qcode': 'loctyp:City'})
            SubElement(located_elm, "name").text = located.get('city')
            self._create_broader_element(located_elm, located.get('state'), 'loctyp:CountryArea')
            self._create_broader_element(located_elm, located.get('country'), 'loctyp:Country')

        if article.get('dateline', {}).get('text', {}):
            SubElement(content_meta, 'dateline').text = article.get('dateline', {}).get('text', {})

    def _format_description(self, article, content_meta):
        """Appends the image description to the contentMeta element

        :param article:
        :param content_meta:
        """
        SubElement(content_meta, 'description', attrib={'role': 'drol:caption'}).text = article.get('description', '')

    def _format_creditline(self, article, content_meta):
        """Append the creditLine to the contentMeta for a picture

        :param article:
        :param content_meta:
        """
        SubElement(content_meta, 'creditline').text = article.get('original_source', article.get('source', ''))

    def _format_groupset(self, article, item):
        """Constructs the groupSet element of a packageItem

        :param article:
        :param item:
        :return: groupSet appended to the item
        """
        groupSet = SubElement(item, 'groupSet', attrib={'root': 'root'})
        for group in article.get(GROUPS, []):
            group_Elem = SubElement(groupSet, 'group', attrib={'id': group.get(GROUP_ID),
                                                               'role': group.get(ROLE)})
            for ref in group.get(REFS, []):
                if ID_REF in ref:
                    SubElement(group_Elem, 'groupRef', attrib={'idref': ref.get(ID_REF)})
                else:
                    if RESIDREF in ref:
                        # get the current archive item being refered to
                        archive_item = superdesk.get_resource_service(ARCHIVE).find_one(req=None,
                                                                                        _id=ref.get(RESIDREF))
                        if archive_item:
                            itemRef = SubElement(group_Elem, 'itemRef',
                                                 attrib={'residref': ref.get(RESIDREF),
                                                         'contenttype': 'application/vnd.iptc.g2.newsitem+xml'})
                            SubElement(itemRef, 'itemClass', attrib={'qcode': 'ninat:' + ref.get(ITEM_TYPE, 'text')})
                            self._format_pubstatus(archive_item, itemRef)
                            self._format_headline(archive_item, itemRef)
                            self._format_slugline(archive_item, itemRef)

    def _format_contentset(self, article, item):
        """Constructs the contentSet element in a picture, video and audio newsItem.

        :param article:
        :param item:
        :return: contentSet Element added to the item
        """
        content_set = SubElement(item, 'contentSet')
        for rendition, value in article.get('renditions', {}).items():
            attrib = {'href': value.get('href'),
                      'contenttype': value.get('mimetype', ''),
                      'rendition': 'rendition:' + rendition
                      }
            if article.get(ITEM_TYPE) == CONTENT_TYPE.PICTURE:
                if 'height' in value:
                    attrib['height'] = str(value.get('height'))
                if 'width' in value:
                    attrib['width'] = str(value.get('width'))
            elif article.get(ITEM_TYPE) in {CONTENT_TYPE.VIDEO, CONTENT_TYPE.AUDIO}:
                if get_filemeta(article, 'width'):
                    attrib['width'] = str(get_filemeta(article, 'width'))
                if get_filemeta(article, 'height'):
                    attrib['height'] = str(get_filemeta(article, 'height'))
                if get_filemeta(article, 'duration'):
                    attrib['duration'] = get_filemeta(article, 'duration')
                    attrib['durationunit'] = 'timeunit:normalPlayTime'

            if rendition == 'original' and get_filemeta(article, 'length'):
                attrib['size'] = str(get_filemeta(article, 'length'))
            SubElement(content_set, 'remoteContent', attrib=attrib)

    def _format_company_codes(self, article, content_meta, item):
        """Format copy codes.

        For each company in the article, appends the subject element to the contentMeta element
        and assert element to item

        :param article: object having published article details
        :type article: dict
        :param content_meta: object representing <contentMeta> in the XML tree
        :type content_meta: lxml.etree.Element
        :param item: object representing <newsItem> in the XML tree
        :type item: lxml.etree.Element
        """

        for company in article.get('company_codes', []):
            literal_name = company['qcode']
            subject = SubElement(content_meta, 'subject',
                                 attrib={'type': 'cpnat:organisation', 'literal': literal_name})
            SubElement(subject, 'name').text = company.get('name', '')

            assert_element = SubElement(item, 'assert', attrib={'literal': literal_name})
            org_details_element = SubElement(assert_element, 'organisationDetails')
            SubElement(org_details_element, 'hasInstrument',
                       attrib={'symbol': company.get('qcode', ''), 'marketlabel': company.get('security_exchange', '')})

    def can_format(self, format_type, article):
        """Method check if the article can be formatted to NewsML G2 or not.

        :param str format_type:
        :param dict article:
        :return: True if article can formatted else False
        """
        return format_type == 'newsmlg2' and \
            article[ITEM_TYPE] in {CONTENT_TYPE.TEXT, CONTENT_TYPE.PREFORMATTED, CONTENT_TYPE.COMPOSITE,
                                   CONTENT_TYPE.PICTURE, CONTENT_TYPE.VIDEO, CONTENT_TYPE.AUDIO}
