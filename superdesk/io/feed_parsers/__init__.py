# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from abc import ABCMeta, abstractmethod

from superdesk.etree import etree
from superdesk.locators.locators import find_cities
from superdesk.metadata.item import Priority


class FeedParser(metaclass=ABCMeta):
    """
    Base class for a Feed Parser.

    A Feed Parser class must have the following attributes:
        1. `NAME` - unique name under which to register the class.
    """

    @abstractmethod
    def can_parse(self, article):
        """
        Sub-classes must override this method and tell whether it can parse the given article.

        :param article: article
        :return: True if the feed parser can parse, False otherwise.
        :rtype: bool
        """
        raise NotImplementedError()

    def set_dateline(self, item, city=None, text=None):
        """
        Sets the 'dateline' to the article identified by item. If city is passed then the system checks if city is
        available in Cities collection. If city is not found in Cities collection then dateline's located is set with
        default values.

        :param item: article.
        :type item: dict
        :param city: Name of the city, if passed the system will search in Cities collection.
        :type city: str
        :param text: dateline in full. For example, "STOCKHOLM, Aug 29, 2014"
        :type text: str
        """

        item['dateline'] = {}

        if city:
            cities = find_cities()
            located = [c for c in cities if c['city'] == city]
            item['dateline']['located'] = located[0] if len(located) > 0 else {'city_code': city, 'city': city,
                                                                               'tz': 'UTC', 'dateline': 'city'}
        if text:
            item['dateline']['text'] = text

    def map_priority(self, source_priority):
        """
        Maps the source priority to superdesk priority

        :param source_priority:
        :type source_priority: str

        :return: priority of the item
        :rtype int
        """

        if source_priority and source_priority.isdigit():
            if int(source_priority) in Priority.values():
                return int(source_priority)

        return Priority.Ordinary.value


class XMLFeedParser(FeedParser, metaclass=ABCMeta):
    """
    Base class for Feed Parsers which can parse the XML Content.
    """

    def __init__(self):
        self.root = None

    @abstractmethod
    def parse_xml(self, xml, provider):
        """
        Parse the ingest XML and extracts the relevant elements/attributes values from the XML.

        :param xml: XML String to parse
        :type xml: str
        :param provider: Ingest Provider Details
        :type provider: dict having properties defined in
                        :py:class: `superdesk.io.ingest_provider_model.IngestProviderResource`
        :return: parsed data as dict.
        :rtype: dict having properties defined in :py:mod: `superdesk.metadata.item`
        """
        raise NotImplementedError()

    def qname(self, tag, ns=None):
        """
        Return the Qualified Name of given XML tag.

        :param tag: XML Tag
        :type tag: str
        :param ns: Namespace to be used for generating Qualified Name, defaults to None.
        :type ns: str
        :return: Qualified Name of tag
        :rtype: str
        """

        if ns is None:
            ns = self.root.tag.rsplit('}')[0].lstrip('{')
        elif ns is not None and ns == 'xml':
            ns = 'http://www.w3.org/XML/1998/namespace'

        return str(etree.QName(ns, tag))


class FileFeedParser(FeedParser, metaclass=ABCMeta):
    """
    Base class for Feed Parsers which can parse the content in a file.
    """

    @abstractmethod
    def parse_file(self, file_path, provider=None):
        """
        Parse the ingest XML and extracts the relevant elements/attributes values from the XML.

        :param file_path: absolute path of the file
        :type file_path: str
        :param provider: Ingest Provider Details, defaults to None.
        :type provider: dict having properties defined in
                        :py:class: `superdesk.io.ingest_provider_model.IngestProviderResource`
        :return: parsed data as dict.
        :rtype: dict having properties defined in :py:mod: `superdesk.metadata.item`
        """
        raise NotImplementedError()


class EmailFeedParser(FeedParser, metaclass=ABCMeta):
    """
    Base class for Feed Parsers which can parse email message.
    """

    @abstractmethod
    def parse_email(self, data, provider):
        """
        Feed Parsers which can ingest articles from an email must override this method and extracts the relevant
        elements/attributes values from the email message.

        :param data:
        :type data: dict
        :param provider: Ingest Provider Details
        :type provider: dict having properties defined in
                        :py:class: `superdesk.io.ingest_provider_model.IngestProviderResource`
        :return: parsed data as dict.
        :rtype: dict having properties defined in :py:mod: `superdesk.metadata.item`
        """
        raise NotImplementedError()


# must be imported for registration
import superdesk.io.feed_parsers.anpa
import superdesk.io.feed_parsers.iptc7901
import superdesk.io.feed_parsers.newsml_1_2
import superdesk.io.feed_parsers.newsml_2_0
import superdesk.io.feed_parsers.nitf
import superdesk.io.feed_parsers.rfc822
import superdesk.io.feed_parsers.wenn_parser
import superdesk.io.feed_parsers.zczc
