# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import time
import logging
from lxml import etree
from lxml.etree import SubElement
from eve.utils import config
from superdesk.publish.formatters import Formatter
import superdesk
from superdesk.errors import FormatterError
from superdesk.etree import parse_html
from superdesk.metadata.item import ITEM_TYPE, CONTENT_TYPE, EMBARGO, ITEM_STATE, CONTENT_STATE,\
    GUID_FIELD
from superdesk.metadata.packages import GROUP_ID, REFS, RESIDREF, ROLE, ROOT_GROUP
from superdesk.utc import utcnow
from flask import current_app as app
from apps  .archive.common import get_utc_schedule
from superdesk.filemeta import get_filemeta

logger = logging.getLogger(__name__)


class NewsML12Formatter(Formatter):
    """
    NewsML 1.2 Formatter
    """

    XML_ROOT = '<?xml version="1.0"?><!DOCTYPE NewsML SYSTEM "http://www.provider.com/dtd/NewsML_1.2.dtd">'
    newml_content_type = {
        CONTENT_TYPE.PICTURE: 'Photo',
        CONTENT_TYPE.AUDIO: 'Audio',
        CONTENT_TYPE.VIDEO: 'Video',
        CONTENT_TYPE.GRAPHIC: 'Graphic',
        CONTENT_TYPE.COMPOSITE: 'ComplexData',
        CONTENT_TYPE.PREFORMATTED: 'Text',
        CONTENT_TYPE.TEXT: 'Text'
    }
    ENCODING = 'UTF-8'

    def format(self, article, subscriber, codes=None):
        """
        Create article in NewsML1.2 format

        :param dict article:
        :param dict subscriber:
        :param list codes:
        :return [(int, str)]: return a List of tuples. A tuple consist of
            publish sequence number and formatted article string.
        :raises FormatterError: if the formatter fails to format an article
        """
        try:
            pub_seq_num = superdesk.get_resource_service('subscribers').generate_sequence_number(subscriber)
            self.now = utcnow()
            self.string_now = self.now.strftime('%Y%m%dT%H%M%S+0000')

            newsml = etree.Element("NewsML")
            SubElement(newsml, "Catalog", {'Href': 'http://www.iptc.org/std/catalog/catalog.IptcMasterCatalog.xml'})
            news_envelope = SubElement(newsml, "NewsEnvelope")
            news_item = SubElement(newsml, "NewsItem")

            self._format_news_envelope(article, news_envelope, pub_seq_num)
            self._format_identification(article, news_item)
            self._format_news_management(article, news_item)
            self._format_news_component(article, news_item)

            return [(pub_seq_num, self.XML_ROOT + etree.tostring(newsml, encoding=self.ENCODING).decode(self.ENCODING))]
        except Exception as ex:
            raise FormatterError.newml12FormatterError(ex, subscriber)

    def _format_news_envelope(self, article, news_envelope, pub_seq_num):
        """
        Create a NewsEnvelope element

        :param dict article:
        :param element news_envelope:
        :param int pub_seq_num:
        """
        SubElement(news_envelope, 'TransmissionId').text = str(pub_seq_num)
        SubElement(news_envelope, 'DateAndTime').text = self.string_now
        SubElement(news_envelope, 'Priority', {'FormalName': str(article.get('priority', 5))})

    def _format_identification(self, article, news_item):
        """
        Creates the Identification element

        :param dict article:
        :param Element news_item:
        """
        revision = self._process_revision(article)
        identification = SubElement(news_item, "Identification")
        news_identifier = SubElement(identification, "NewsIdentifier")
        date_id = article.get('firstcreated').strftime("%Y%m%d")
        SubElement(news_identifier, 'ProviderId').text = app.config['NEWSML_PROVIDER_ID']
        SubElement(news_identifier, 'DateId').text = date_id
        SubElement(news_identifier, 'NewsItemId').text = article[GUID_FIELD]
        SubElement(news_identifier, 'RevisionId', attrib=revision).text = str(article.get(config.VERSION, ''))
        SubElement(news_identifier, 'PublicIdentifier').text = \
            self._generate_public_identifier(article[config.ID_FIELD], article.get(config.VERSION, ''),
                                             revision.get('Update', ''))
        SubElement(identification, "DateLabel").text = self.now.strftime("%A %d %B %Y")

    def _generate_public_identifier(self, item_id, version, update):
        """
        Create the NewsML public identifier

        :param str item_id: Article Id
        :param str version: Article Version
        :param str update: update
        :return: returns public identifier
        """
        return '%s:%s%s' % (item_id, version, update)

    def _process_revision(self, article):
        """
        Get attributes of RevisionId element.

        :param dict article:
        :return: dict
        """
        revision = {'PreviousRevision': '0', 'Update': 'N'}
        if article.get(ITEM_STATE) in {CONTENT_STATE.CORRECTED, CONTENT_STATE.KILLED, CONTENT_STATE.RECALLED}:
            revision['PreviousRevision'] = str(article.get(config.VERSION) - 1)
        return revision

    def _format_news_management(self, article, news_item):
        """
        Create a NewsManagement element

        :param dict article:
        :param Element news_item:
        """
        news_management = SubElement(news_item, "NewsManagement")
        SubElement(news_management, 'NewsItemType', {'FormalName': 'News'})
        SubElement(news_management, 'FirstCreated').text = \
            article['firstcreated'].strftime('%Y%m%dT%H%M%S+0000')
        SubElement(news_management, 'ThisRevisionCreated').text = \
            article['versioncreated'].strftime('%Y%m%dT%H%M%S+0000')

        if article.get(EMBARGO):
            SubElement(news_management, 'Status', {'FormalName': 'Embargoed'})
            status_will_change = SubElement(news_management, 'StatusWillChange')
            SubElement(status_will_change, 'FutureStatus', {'FormalName': article['pubstatus']})
            SubElement(status_will_change, 'DateAndTime').text = \
                get_utc_schedule(article, EMBARGO).isoformat()
        else:
            SubElement(news_management, 'Status', {'FormalName': article['pubstatus']})

        if article.get('urgency'):
            SubElement(news_management, 'Urgency', {'FormalName': str(article['urgency'])})

        if article['state'] == 'corrected':
            SubElement(news_management, 'Instruction', {'FormalName': 'Correction'})
        else:
            SubElement(news_management, 'Instruction', {'FormalName': 'Update'})

    def _format_news_component(self, article, news_item):
        """
        Create a main NewsComponent element

        :param dict article:
        :param Element news_item:
        """
        news_component = SubElement(news_item, "NewsComponent")
        main_news_component = SubElement(news_component, "NewsComponent")
        SubElement(main_news_component, 'Role', {'FormalName': 'Main'})
        self._format_news_lines(article, main_news_component)
        self._format_rights_metadata(article, main_news_component)
        self._format_descriptive_metadata(article, main_news_component)

        for company in article.get('company_codes', []):
            metadata = SubElement(main_news_component, 'Metadata')
            SubElement(metadata, 'MetadataType', attrib={'FormalName': 'Securities Identifier'})
            SubElement(metadata, 'Property', attrib={'FormalName': 'Name', 'Value': company.get('name', '')})
            SubElement(metadata, 'Property', attrib={'FormalName': 'Ticker Symbol', 'Value': company.get('qcode', '')})
            SubElement(metadata, 'Property', attrib={'FormalName': 'Exchange',
                                                     'Value': company.get('security_exchange', '')})

        if article.get(ITEM_TYPE) == CONTENT_TYPE.COMPOSITE:
            self._format_package(article, main_news_component)
        elif article.get(ITEM_TYPE) in {CONTENT_TYPE.TEXT, CONTENT_TYPE.PREFORMATTED, CONTENT_TYPE.COMPOSITE}:
            self._format_abstract(article, main_news_component)
            self._format_body(article, main_news_component)
        elif article.get(ITEM_TYPE) in {CONTENT_TYPE.VIDEO, CONTENT_TYPE.AUDIO, CONTENT_TYPE.PICTURE}:
            self._format_media(article, main_news_component, self.newml_content_type[article.get(ITEM_TYPE)])

    def _format_news_lines(self, article, main_news_component):
        """
        Create a NewsLines element

        :param dict article:
        :param Element main_news_component:
        """
        news_lines = SubElement(main_news_component, "NewsLines")
        if article.get('headline'):
            SubElement(news_lines, 'HeadLine').text = article.get('headline')
        if article.get('byline'):
            SubElement(news_lines, 'ByLine').text = article.get('byline') or ''
        if article.get('dateline', {}).get('text', ''):
            SubElement(news_lines, 'DateLine').text = article.get('dateline', {}).get('text', '')
        SubElement(news_lines, 'CreditLine').text = article.get('original_source', article.get('source', ''))
        if article.get('slugline', ''):
            SubElement(news_lines, 'KeywordLine').text = article.get('slugline', '')
        # TODO: may be we need to create our own catalog for the NewsLineType
        if article.get('ednote'):
            news_line = SubElement(news_lines, 'NewsLine')
            SubElement(news_line, 'NewsLineType', attrib={'FormalName': 'EditorialNote'})
            SubElement(news_line, 'NewsLineText').text = article.get('ednote')

    def _format_rights_metadata(self, article, main_news_component):
        """
        Create a RightsMetadata element

        :param dict article:
        :param Element main_news_component:
        """
        rights = superdesk.get_resource_service('vocabularies').get_rightsinfo(article)

        rights_metadata = SubElement(main_news_component, "RightsMetadata")
        copyright = SubElement(rights_metadata, "Copyright")
        SubElement(copyright, 'CopyrightHolder').text = rights['copyrightholder']
        SubElement(copyright, 'CopyrightDate').text = self.now.strftime("%Y")

        usage_rights = SubElement(rights_metadata, "UsageRights")
        SubElement(usage_rights, 'UsageType').text = rights['copyrightnotice']
        # SubElement(usage_rights, 'Geography').text = article.get('place', article.get('located', ''))
        SubElement(usage_rights, 'RightsHolder').text = article.get('original_source', article.get('source', ''))
        SubElement(usage_rights, 'Limitations').text = rights['usageterms']
        SubElement(usage_rights, 'StartDate').text = self.string_now
        SubElement(usage_rights, 'EndDate').text = self.string_now

    def _format_descriptive_metadata(self, article, main_news_component):
        """
        Create a Descriptive_metadata element

        :param dict article:
        :param Element main_news_component:
        """
        descriptive_metadata = SubElement(main_news_component, "DescriptiveMetadata")
        subject_code = SubElement(descriptive_metadata, "SubjectCode")

        for subject in article.get('subject', []):
            SubElement(subject_code, 'Subject', {'FormalName': subject.get('qcode', '')})

        self._format_dateline(article, descriptive_metadata)
        self._format_place(article, descriptive_metadata)

        if 'anpa_category' in article:
            for category in article.get('anpa_category', []):
                SubElement(descriptive_metadata, 'Property',
                           {'FormalName': 'Category', 'Value': category['qcode']})

    def _format_place(self, article, descriptive_metadata):
        """
        Create Place specific element in the descriptive metadata

        :param dict article:
        :param Element descriptive_metadata:
        """
        if not article.get('place'):
            return

        for place in article.get('place'):
            if place.get('country') or place.get('state') or place.get('world_region'):
                location = SubElement(descriptive_metadata,
                                      'Location', attrib={'HowPresent': 'RelatesTo'})
                if place.get('state'):
                    SubElement(location, 'Property',
                               {'FormalName': 'CountryArea', 'Value': place.get('state')})
                if place.get('country'):
                    SubElement(location, 'Property',
                               {'FormalName': 'Country', 'Value': place.get('country')})
                if place.get('world_region'):
                    SubElement(location, 'Property',
                               {'FormalName': 'WorldRegion', 'Value': place.get('world_region')})

    def _format_dateline(self, article, descriptive_metadata):
        """
        Create the DateLineDate and Location in the descriptive metadata

        :param dict article:
        :param Element news_lines:
        """
        located = article.get('dateline', {}).get('located')
        if located:
            location_elm = SubElement(descriptive_metadata, 'Location', attrib={'HowPresent': 'Origin'})
            if located.get('city'):
                SubElement(location_elm, 'Property',
                           attrib={'FormalName': 'City', 'Value': located.get('city')})
            if located.get('state'):
                SubElement(location_elm, 'Property',
                           attrib={'FormalName': 'CountryArea', 'Value': located.get('state')})
            if located.get('country'):
                SubElement(location_elm, 'Property',
                           attrib={'FormalName': 'Country', 'Value': located.get('country')})

    def _format_abstract(self, article, main_news_component):
        """
        Create an abstract NewsComponent element

        :param dict article:
        :param Element main_news_component:
        """
        abstract_news_component = SubElement(main_news_component, "NewsComponent")
        SubElement(abstract_news_component, 'Role', {'FormalName': 'Abstract'})
        content_item = SubElement(abstract_news_component, "ContentItem")
        SubElement(content_item, 'MediaType', {'FormalName': 'Text'})
        SubElement(content_item, 'Format', {'FormalName': 'Text'})
        abstract = parse_html(article.get('abstract', ''))
        SubElement(content_item, 'DataContent').text = etree.tostring(abstract, encoding="unicode", method="text")

    def _format_body(self, article, main_news_component):
        """
        Create an body text NewsComponent element

        :param dict article:
        :param Element main_news_component:
        """
        body_news_component = SubElement(main_news_component, "NewsComponent")
        SubElement(body_news_component, 'Role', {'FormalName': 'BodyText'})
        content_item = SubElement(body_news_component, "ContentItem")
        SubElement(content_item, 'MediaType', {'FormalName': 'Text'})
        SubElement(content_item, 'Format', {'FormalName': 'NITF'})
        data_content = SubElement(content_item, 'DataContent')
        nitf = SubElement(data_content, 'nitf')
        body = SubElement(nitf, 'body')
        body_content = SubElement(body, 'body.content')
        self.map_html_to_xml(body_content, self.append_body_footer(article))

    def _format_description(self, article, main_news_component):
        """
        Create an description NewsComponent element

        :param dict article:
        :param Element main_news_component:
        """
        desc_news_component = SubElement(main_news_component, "NewsComponent")
        SubElement(desc_news_component, 'Role', {'FormalName': 'Description'})
        content_item = SubElement(desc_news_component, "ContentItem")
        SubElement(content_item, 'MediaType', {'FormalName': 'Text'})
        SubElement(content_item, 'Format', {'FormalName': 'Text'})
        SubElement(content_item, 'DataContent').text = self.append_body_footer(article)

    def _format_media(self, article, main_news_component, media_type):
        """
        Create an NewsComponent element related to media

        :param dict article:
        :param Element main_news_component:
        """
        media_news_component = SubElement(main_news_component, "NewsComponent")
        SubElement(media_news_component, 'Role', {'FormalName': media_type})
        for rendition, value in article.get('renditions').items():
            news_component = SubElement(media_news_component, "NewsComponent")
            SubElement(news_component, 'Role', {'FormalName': rendition})
            content_item = SubElement(news_component, "ContentItem",
                                      attrib={'Href': value.get('href', '')})
            SubElement(content_item, 'MediaType', {'FormalName': media_type})
            SubElement(content_item, 'Format', {'FormalName': value.get('mimetype', '')})
            characteristics = SubElement(content_item, 'Characteristics')
            if rendition == 'original' and get_filemeta(article, 'length'):
                SubElement(characteristics, 'SizeInBytes').text = str(get_filemeta(article, 'length'))
            if article.get(ITEM_TYPE) == CONTENT_TYPE.PICTURE:
                if value.get('width'):
                    SubElement(characteristics, 'Property',
                               attrib={'FormalName': 'Width', 'Value': str(value.get('width'))})
                if value.get('height'):
                    SubElement(characteristics, 'Property',
                               attrib={'FormalName': 'Height', 'Value': str(value.get('height'))})
            elif article.get(ITEM_TYPE) in {CONTENT_TYPE.VIDEO, CONTENT_TYPE.AUDIO}:
                if get_filemeta(article, 'width'):
                    SubElement(characteristics, 'Property',
                               attrib={'FormalName': 'Width',
                                       'Value': str(get_filemeta(article, 'width'))})
                if get_filemeta(article, 'height'):
                    SubElement(characteristics, 'Property',
                               attrib={'FormalName': 'Height',
                                       'Value': str(get_filemeta(article, 'height'))})

                duration = self._get_total_duration(get_filemeta(article, 'duration'))
                if duration:
                    SubElement(characteristics, 'Property',
                               attrib={'FormalName': 'TotalDuration', 'Value': str(duration)})

    def _format_package(self, article, main_news_component):
        """
        Constructs the NewsItemRef for packages.

        :param dict article:
        :param Element main_news_component:
        """
        news_component = SubElement(main_news_component, 'NewsComponent')
        SubElement(news_component, 'Role', {'FormalName': 'root'})
        for group in [group for group in article.get('groups', []) if group.get(GROUP_ID) != ROOT_GROUP]:
            sub_news_component = SubElement(news_component, 'NewsComponent')
            SubElement(sub_news_component, 'Role', attrib={'FormalName': group.get(ROLE, '')})
            for ref in group.get(REFS, []):
                if RESIDREF in ref:
                    revision = self._process_revision({})
                    item_ref = self._generate_public_identifier(ref.get(RESIDREF), ref.get(config.VERSION),
                                                                revision.get('Update', ''))
                    SubElement(sub_news_component, 'NewsItemRef', attrib={'NewsItem': item_ref})

    def _get_total_duration(self, duration):
        """
        Get the duration in seconds.

        :param str duration: Format required is '%H:%M:%S.%f'. For example, 1:01:12.0000 or 1:1:12.0000
        :return int:
        """
        total_seconds = 0
        try:
            ts = time.strptime(duration, '%H:%M:%S.%f')
            total_seconds = ts.tm_sec + (ts.tm_min * 60) + (ts.tm_hour * 60 * 60)
        except Exception:
            logger.error('Failed to get total seconds for duration:{}'.format(duration))
        return total_seconds

    def can_format(self, format_type, article):
        """
        Test if the article can be formatted to NewsML 1.2 or not.

        :param str format_type:
        :param dict article:
        :return: True if article can formatted else False
        """
        return format_type == 'newsml12' and \
            article[ITEM_TYPE] in {CONTENT_TYPE.TEXT, CONTENT_TYPE.PREFORMATTED, CONTENT_TYPE.COMPOSITE,
                                   CONTENT_TYPE.PICTURE, CONTENT_TYPE.VIDEO, CONTENT_TYPE.AUDIO}
