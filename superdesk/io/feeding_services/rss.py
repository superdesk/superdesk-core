# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


import feedparser
import requests

from calendar import timegm
from collections import namedtuple
from datetime import datetime

from superdesk.errors import IngestApiError, ParserError
from superdesk.io import register_feeding_service
from superdesk.io.feeding_services import FeedingService
from superdesk.metadata.item import ITEM_TYPE, CONTENT_TYPE, GUID_TAG
from superdesk.utils import merge_dicts
from superdesk.metadata.utils import generate_guid

from urllib.parse import quote as urlquote, urlsplit, urlunsplit


utcfromtimestamp = datetime.utcfromtimestamp


class RSSFeedingService(FeedingService):
    """
    Feeding service for providing feeds received in RSS 2.0 format.

    (NOTE: it should also work with other syndicated feeds formats, too, since
    the underlying parser supports them, but for our needs RSS 2.0 is assumed)
    """

    NAME = 'rss'
    ERRORS = [IngestApiError.apiAuthError().get_error_description(),
              IngestApiError.apiNotFoundError().get_error_description(),
              IngestApiError.apiGeneralError().get_error_description(),
              ParserError.parseMessageError().get_error_description()]

    ItemField = namedtuple('ItemField', ['name', 'name_in_data', 'type'])

    item_fields = [
        ItemField('guid', 'guid', str),
        ItemField('uri', 'guid', str),
        ItemField('firstcreated', 'published_parsed', datetime),
        ItemField('versioncreated', 'updated_parsed', datetime),
        ItemField('headline', 'title', str),
        ItemField('abstract', 'summary', str),
        ItemField('body_html', 'body_text', str),
    ]
    """A list of fields that items created from the ingest data should contain.

    Each list item is a named tuple with the following three attribues:

    * name - the name of the field (attribute) in the resulting ingest item
    * name_in_data - the expected name of the data field in the retrieved
        ingest data (this can be overriden by providing a field name alias)
    * type - field's data type
    """

    IMG_MIME_TYPES = (
        'image/gif',
        'image/jpeg',
        'image/png',
        'image/tiff',
    )
    """
    Supported MIME types for ingesting external images referenced by the
    RSS entries.
    """

    IMG_FILE_SUFFIXES = ('.gif', '.jpeg', '.jpg', '.png', '.tif', '.tiff')
    """
    Supported image filename extensions for ingesting (used for the
    <media:thumbnail> tags - they lack the "type" attribute).
    """

    def __init__(self):
        super().__init__()
        self.auth_info = None

    def prepare_href(self, url, mimetype=None):
        """Prepare a link to an external resource (e.g. an image file).

        It can be directly used by the ingest machinery for fetching it.

        If provider requires authentication, basic HTTP authentication info is
        added to the given url, otherwise it is returned unmodified.

        :param str url: the original URL as extracted from an RSS entry

        :return: prepared URL
        :rtype: str
        """
        if self.auth_info:
            userinfo_part = '{}:{}@'.format(
                urlquote(self.auth_info['username']),
                urlquote(self.auth_info['password'])
            )
            scheme, netloc, path, query, fragment = urlsplit(url)
            netloc = userinfo_part + netloc
            url = urlunsplit((scheme, netloc, path, query, fragment))

        return url

    def _update(self, provider):
        """
        Check data provider for data updates and returns new items (if any).

        :param provider: data provider instance
        :return: a list containing a list of new content items
        :rtype: list

        :raises IngestApiError: if data retrieval error occurs
        :raises ParserError: if retrieved RSS data cannot be parsed
        """
        config = provider.get('config', {})

        if config.get('auth_required'):
            self.auth_info = {
                'username': config.get('username', ''),
                'password': config.get('password', '')
            }

        try:
            xml_data = self._fetch_data(config, provider)
            data = feedparser.parse(xml_data)
        except IngestApiError:
            raise
        except Exception as ex:
            raise ParserError.parseMessageError(ex, provider)

        # If provider last updated time is not available, set it to 1.1.1970
        # so that it will be recognized as "not up to date".
        # Also convert it to a naive datetime object (removing tzinfo is fine,
        # because it is in UTC anyway)
        t_provider_updated = provider.get('last_updated', utcfromtimestamp(0))
        t_provider_updated = t_provider_updated.replace(tzinfo=None)

        new_items = []
        field_aliases = config.get('field_aliases')

        for entry in data.entries:
            t_entry_updated = utcfromtimestamp(timegm(entry.updated_parsed))

            if t_entry_updated <= t_provider_updated:
                continue

            item = self._create_item(entry, field_aliases, provider.get('source', None))
            self.add_timestamps(item)

            # If the RSS entry references any images, create picture items from
            # them and create a package referencing them and the entry itself.
            # If there are no image references, treat entry as a simple text
            # item, even if it might reference other media types, e.g. videos.
            image_urls = self._extract_image_links(entry)
            if image_urls:
                image_items = self._create_image_items(image_urls, item)
                new_items.extend(image_items)
                new_items.append(item)
                item = self._create_package(item, image_items)

            new_items.append(item)

        return [new_items]

    def _fetch_data(self, config, provider):
        """Fetch the latest feed data.

        :param dict config: RSS resource configuration
        :param provider: data provider instance, needed as an argument when
            raising ingest errors
        :return: fetched RSS data
        :rtype: str

        :raises IngestApiError: if fetching data fails for any reason
            (e.g. authentication error, resource not found, etc.)
        """
        url = config['url']

        if config.get('auth_required', False):
            auth = (config.get('username'), config.get('password'))
        else:
            auth = None

        response = requests.get(url, auth=auth)

        if response.ok:
            return response.content
        else:
            if response.status_code in (401, 403):
                raise IngestApiError.apiAuthError(
                    Exception(response.reason), provider)
            elif response.status_code == 404:
                raise IngestApiError.apiNotFoundError(
                    Exception(response.reason), provider)
            else:
                raise IngestApiError.apiGeneralError(
                    Exception(response.reason), provider)

    def _extract_image_links(self, rss_entry):
        """Extract URLs of all images referenced by the given RSS entry.

        Images can be referenced via `<enclosure>`, `<media:thumbnail>` or
        `<media:content>` RSS tag and must be listed among the allowed image
        types. All other links to external media are ignored.

        Duplicate URLs are omitted from the result.

        :param rss_entry: parsed RSS item (entry)
        :type rss_entry: :py:class:`feedparser.FeedParserDict`

        :return: a list of all unique image URLs found (as strings)
        """
        img_links = set()

        for link in getattr(rss_entry, 'links', []):
            if link.get('type') in self.IMG_MIME_TYPES:
                img_links.add(link['href'])

        for item in getattr(rss_entry, 'media_thumbnail', []):
            url = item.get('url', '')
            if url.endswith(self.IMG_FILE_SUFFIXES):
                img_links.add(url)

        for item in getattr(rss_entry, 'media_content', []):
            if item.get('type') in self.IMG_MIME_TYPES:
                img_links.add(item['url'])

        return list(img_links)

    def _create_item(self, data, field_aliases=None, source=None):
        """Create a new content item from RSS feed data.

        :param dict data: parsed data of a single feed entry
        :param field_aliases: (optional) field name aliases. Used for content
             fields that are named differently in retrieved data.
        :type field_aliases: list of {field_name: alias} dictionaries or None
        :param str source: the source of provider

        :return: created content item
        :rtype: dict
        """
        if field_aliases is None:
            field_aliases = {}
        else:
            field_aliases = merge_dicts(field_aliases)
        aliased_fields = set(field_aliases.values())

        item = dict(type=CONTENT_TYPE.TEXT)

        # Only consider fields that are not used as an alias (i.e. used to
        # populate another field) - unless those fields have their own
        # aliases, too.
        # The idea is that if e.g. the main text field is aliased to use the
        # parsed data's summary field, that summary should not be used to
        # populate the field it was originally meant for.
        fields_to_consider = (
            f for f in self.item_fields
            if (f.name_in_data not in aliased_fields) or
               (f.name_in_data in aliased_fields and
                f.name_in_data in field_aliases)
        )

        for field in fields_to_consider:
            data_field_name = field_aliases.get(
                field.name_in_data, field.name_in_data
            )
            field_value = data.get(data_field_name)

            if (field.type is datetime) and field_value:
                field_value = utcfromtimestamp(timegm(field_value))

            item[field.name] = field_value

            # Some feeds use <content:encoded> tag for storing the main content,
            # and that tag is parsed differently. If the body_html has not been
            # found in its default data field and is not aliased, try to
            # populate it using the aforementioned content field as a fallback.
            if (
                field.name == 'body_html' and
                not field_value and
                field.name_in_data not in field_aliases
            ):
                try:
                    item['body_html'] = data.content[0].value
                except:
                    pass  # content either non-existent or parsed differently

        if item.get('uri', None):
            if not item.get('body_html', None):
                item['body_html'] = ''
            source = source or 'source'
            item['body_html'] = '<p><a href="%s" target="_blank">%s</a></p>' % (item['uri'], source) + item['body_html']
        return item

    def _create_image_items(self, image_links, text_item):
        """Create a list of picture items that represent the external images located on given URLs.

        Each created item's `firstcreated` and `versioncreated` fields are set
        to the same value as the values of these fields in `text_item`.

        :param iterable image_links: list of image URLs
        :param dict text_item: the "main" text item the images are related to

        :return: list of created image items (as dicts)
        """
        image_items = []

        for image_url in image_links:
            img_item = {
                'guid': generate_guid(type=GUID_TAG),
                ITEM_TYPE: CONTENT_TYPE.PICTURE,
                'firstcreated': text_item.get('firstcreated'),
                'versioncreated': text_item.get('versioncreated'),
                'renditions': {
                    'baseImage': {
                        'href': image_url
                    }
                }
            }
            image_items.append(img_item)

        return image_items

    def _create_package(self, text_item, image_items):
        """Create a new content package from given content items.

        The package's `main` group contains only the references to given items,
        not the items themselves. In the list of references, the reference to
        the text item preceeds the references to image items.

        Package's `firstcreated` and `versioncreated` fields are set to values
        of these fields in `text_item`, and the `headline` is copied as well.

        :param dict text_item: item representing the text content
        :param list image_items: list of items (dicts) representing the images
            related to the text content
        :return: the created content package
        :rtype: dict
        """
        package = {
            ITEM_TYPE: CONTENT_TYPE.COMPOSITE,
            'guid': generate_guid(type=GUID_TAG),
            'firstcreated': text_item['firstcreated'],
            'versioncreated': text_item['versioncreated'],
            'headline': text_item.get('headline', ''),
            'groups': [
                {
                    'id': 'root',
                    'role': 'grpRole:NEP',
                    'refs': [{'idRef': 'main'}],
                }, {
                    'id': 'main',
                    'role': 'main',
                    'refs': [],
                }
            ]
        }

        item_references = package['groups'][1]['refs']
        item_references.append({'residRef': text_item['guid']})

        for image in image_items:
            item_references.append({'residRef': image['guid']})

        return package


register_feeding_service(RSSFeedingService.NAME, RSSFeedingService(), RSSFeedingService.ERRORS)
