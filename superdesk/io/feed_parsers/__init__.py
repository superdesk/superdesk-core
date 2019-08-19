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

from superdesk.etree import etree as sd_etree
from superdesk.errors import SkipValue
from flask import current_app as app
from superdesk.metadata.item import Priority
from collections import OrderedDict
import inspect
from lxml import etree
import superdesk
import logging

logger = logging.getLogger(__name__)


class FeedParser(metaclass=ABCMeta):
    """
    Base class for a Feed Parser.

    A Feed Parser class must have the following attributes:
        1. `NAME` - unique name under which to register the class.
    """

    @abstractmethod
    def can_parse(self, article):
        """Sub-classes must override this method and tell whether it can parse the given article.

        :param article: article
        :return: True if the feed parser can parse, False otherwise.
        :rtype: bool
        """
        raise NotImplementedError()

    @abstractmethod
    def parse(self, article, provider=None):
        """Parse the given article and extracts the relevant elements/attributes values from the given article.

        :param article: XML String to parse
        :type article: str
        :param provider: Ingest Provider Details, defaults to None
        :type provider: dict having properties defined in
                        :py:class: `superdesk.io.ingest_provider_model.IngestProviderResource`
        :return: parsed data as dict.
        :rtype: dict having properties defined in :py:mod: `superdesk.metadata.item`
        """
        raise NotImplementedError()

    def set_dateline(self, item, city=None, text=None):
        """Sets the 'dateline' to the article identified by item.

        If city is passed then the system checks if city is available in Cities collection.
        If city is not found in Cities collection then dateline's located is set with default values.

        :param item: article.
        :type item: dict
        :param city: Name of the city, if passed the system will search in Cities collection.
        :type city: str
        :param text: dateline in full. For example, "STOCKHOLM, Aug 29, 2014"
        :type text: str
        """

        item.setdefault('dateline', {})

        if city:
            cities = app.locators.find_cities()
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
        self.metadata_mapping = None

    def _parse_mapping(self, value):
        if isinstance(value, dict):
            if 'default_attr' in value:
                if 'default' in value:
                    logger.error("default and default_attr can't be used at the same time,"
                                 "only default will be used ({})".format(self.__class__))
                if 'xpath':
                    if '/' not in 'xpath':
                        logger.info("default_attr can be used for simple child element ({})".format(self.__class__))
                else:
                    logger.error("xpath is needed when default_attr is used ({})".format(self.__class__))
            if 'callback' in value and 'list' in value:
                del value['list']
                logger.error("list can't ve used with callback ({})".format(self.__class__))
            return value
        elif isinstance(value, str):
            if not value:
                return {}
            return {'xpath': value}
        elif callable(value):
            # if callable has 2 arguments, it's a callback_with_item
            params = inspect.signature(value).parameters
            if len(params) == 2:
                return {'callback_with_item': value}
            elif len(params) == 1:
                return {'callback': value}
            else:
                logger.error("Invalid signature for parser callback, ignoring")
                return {}
        else:
            logger.warn("Can't parse mapping value {}, ignoring it".format(value))
            return {}

    def _generate_mapping(self, setting_param_name):
        """Generate self.metadata_mapping according to available mappings.

        The following mappings are used in this order (last is more important):
            - self.default_mapping
            - self.MAPPING, intended for subclasses
            - [setting_param_name] dictionary which can be put in settings
        If a value is a non-empty string, it is a xpath, @attribute can be used as last path component.
        If value is empty string/dict, the key will be ignored
        If value is a callable, if is used either as "callback" or "callback_with_item" (see below) depending on
            its number of arguments ("callback" is used if it has only one argument, "callback_with_item" is
            used if it has 2 arguments, else an error is logged)
        If a dictionary is used as value, following keys can be used:
            xpath: path to the element
            callback: callback executed with nitf Element as argument, return value will be used
                SkipValue can be raised to ignore the value
            callback_with_item: callback wich use nift element and item as arguments
                the callback must store itself the argument in the item dict, return value is not used
            default: value to use if element/attribute doesn't exists (default: doesn't set the key)
            list: a bool which indicate if a list is expected
                  if False (default), only first value is used
            filter: callable to be used with found element/value
                value returned by the callable will be used
                if None is returned, value will be ignored
                In case of multiple values (i.e. if "list" is set), filter is called on each item
            default_attr: value if element exist but attribute is missing
                this works actually for all values, if it is not found parent element is checked
                and default_attr is used only if parent element exists
            key_hook: a callable which store itself the resulting value in the item,
                      usefull for specific behaviours when several values goes to same key
                      callable will get item and value as arguments.
            update: a bool which indicate that default mapping must be updated instead of overwritten
        Note the difference between using a callable directly, and "filter" in a dict:
        the former get the root element and can be skipped with SkipValue, while the
        later get an element/value found with xpath.
        """
        try:
            class_mapping = self.MAPPING
        except AttributeError:
            class_mapping = {}

        if setting_param_name is not None:
            settings_mapping = getattr(superdesk.config, setting_param_name)
            if settings_mapping is None:
                logging.info("No mapping found in settings for NITF parser, using default one")
                settings_mapping = {}
        else:
            settings_mapping = {}

        mapping = self.metadata_mapping = OrderedDict()

        for source_mapping in (self.default_mapping, class_mapping, settings_mapping):
            for key, value in source_mapping.items():
                key_mapping = self._parse_mapping(value)
                if key_mapping.get('update', False) and key in mapping:
                    mapping[key].update(key_mapping)
                else:
                    mapping[key] = key_mapping

    def do_mapping(self, item, item_xml, setting_param_name=None, namespaces=None):
        """Apply mapping to item's XML content to get article metadata

        mapping is generated by self._generate_mapping
        :param item: dictionary to fill with item metadata
        :type item: dict
        :param item_xml: XML element to parse
        :type item_xml: lxml.etree.Element
        :param setting_param_name: name of the settings attribute containing the mapping
        :type setting_param_name: str
        :type setting_param_name: NoneType
        :param namespaces: namespaces map to use with lxml methods
        :type namespaces: dict
        :type namespaces: NoneType
        """
        if self.metadata_mapping is None:
            self._generate_mapping(setting_param_name)

        for key, mapping in self.metadata_mapping.items():
            if not mapping:
                # key is ignored
                continue
            try:
                xpath = mapping['xpath']
            except KeyError:
                # no xpath, we must have a callable
                if 'callback_with_item' in mapping:
                    # callback_with_item store values themselves, so we continue after calling it
                    mapping['callback_with_item'](item_xml, item)
                    continue
                if 'callback' not in mapping:
                    logging.warn("invalid mapping for key {}, ignoring it".format(key))
                    continue
                try:
                    values = [mapping['callback'](item_xml)]
                except SkipValue:
                    continue
                list_ = False
            else:
                values = item_xml.xpath(xpath, namespaces=namespaces)
                list_ = mapping.get('list', False)
                if not list_:
                    if isinstance(values, list):
                        values = values[:1]
                    else:
                        # result was not a list, can happen if a function
                        # has been used
                        values = [values]
                if not values:
                    # nothing found, we check default
                    try:
                        values = [mapping['default']]
                    except KeyError:
                        if 'default_attr' in mapping:
                            parent = item_xml.xpath(xpath[:xpath.rfind('/')], namespaces=namespaces)
                            if parent:
                                # default_attr is only used when there is a parent element
                                values = [mapping['default_attr']]
                            else:
                                continue
                        else:
                            # if there is not default value we skip the key
                            continue
                else:
                    for idx, current_value in enumerate(values):

                        if isinstance(current_value, etree._Element):
                            # do we want a filter or the content?
                            try:
                                # filter
                                filter_cb = mapping['filter']
                            except KeyError:
                                # content
                                values[idx] = ''.join(current_value.itertext())
                            else:
                                values[idx] = filter_cb(current_value)
                        else:
                            if 'filter' in mapping:
                                values[idx] = mapping['filter'](current_value)

                    if None in values:
                        # filter can return None to skip a value
                        values = [v for v in values if v is not None]
                        if not values and not list_:
                            continue

            value = values if list_ else values[0]
            if 'key_hook' in mapping:
                mapping['key_hook'](item, value)
            else:
                item[key] = value

        return item

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

        return str(sd_etree.QName(ns, tag))


class FileFeedParser(FeedParser, metaclass=ABCMeta):
    """
    Base class for Feed Parsers which can parse the content in a file.
    """

    pass


class EmailFeedParser(FeedParser, metaclass=ABCMeta):
    """
    Base class for Feed Parsers which can parse email message.
    """

    pass


# must be imported for registration
from superdesk.io.feed_parsers.anpa import ANPAFeedParser  # NOQA
from superdesk.io.feed_parsers.iptc7901 import IPTC7901FeedParser  # NOQA
from superdesk.io.feed_parsers.newsml_1_2 import NewsMLOneFeedParser  # NOQA
from superdesk.io.feed_parsers.newsml_2_0 import NewsMLTwoFeedParser  # NOQA
from superdesk.io.feed_parsers.nitf import NITFFeedParser  # NOQA
from superdesk.io.feed_parsers.rfc822 import EMailRFC822FeedParser  # NOQA
from superdesk.io.feed_parsers.wenn_parser import WENNFeedParser  # NOQA
from superdesk.io.feed_parsers.dpa_iptc7901 import DPAIPTC7901FeedParser  # NOQA
from superdesk.io.feed_parsers.afp_newsml_1_2 import AFPNewsMLOneFeedParser  # NOQA
from superdesk.io.feed_parsers.scoop_newsml_2_0 import ScoopNewsMLTwoFeedParser  # NOQA
from superdesk.io.feed_parsers.ap_anpa import AP_ANPAFeedParser  # NOQA
from superdesk.io.feed_parsers.pa_nitf import PAFeedParser  # NOQA
from superdesk.io.feed_parsers.efe_nitf import EFEFeedParser  # NOQA
from superdesk.io.feed_parsers.wordpress_wxr import WPWXRFeedParser  # NOQA
from superdesk.io.feed_parsers.ninjs import NINJSFeedParser  # NOQA
from superdesk.io.feed_parsers.stt_newsml import STTNewsMLFeedParser  # NOQA
from superdesk.io.feed_parsers.ritzau import RitzauFeedParser  # NOQA
from superdesk.io.feed_parsers.image_iptc import ImageIPTCFeedParser  # NOQA
from superdesk.io.feed_parsers.ana_mpe_newsml import ANANewsMLOneFeedParser  # NOQA
from superdesk.io.feed_parsers.bbc_ninjs import BBCNINJSFeedParser  # NOQA
from superdesk.io.feed_parsers.ap_media import APMediaFeedParser  # NOQA