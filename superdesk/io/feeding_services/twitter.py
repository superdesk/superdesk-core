# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import re
import hashlib
from dateutil import parser

from superdesk.errors import IngestTwitterError
from superdesk.io.registry import register_feeding_service
from superdesk.io.feeding_services import FeedingService
from superdesk.metadata.utils import generate_guid
from superdesk.metadata.item import ITEM_TYPE, CONTENT_TYPE, GUID_TAG

import twitter


class TwitterFeedingService(FeedingService):
    """
    Feeding Service class which can read feed from multiple Twitter
    Screen Names and also hashtags
    """

    NAME = 'twitter'
    label = 'Twitter'

    ERRORS = [IngestTwitterError.TwitterLoginError().get_error_description(),
              IngestTwitterError.TwitterNoScreenNamesError().
              get_error_description()]

    def _test(self, provider):
        self._update(provider, update=None, test=True)

    def _update(self, provider, update, test=False):
        config = provider.get('config', {})
        consumer_key = config.get('consumer_key', '')
        consumer_secret = config.get('consumer_secret', '')
        access_token_key = config.get('access_token_key', '')
        access_token_secret = config.get('access_token_secret', '')
        screen_names = config.get('screen_names', '')
        status_count = 100
        # how many statuses to get, 200 should be max

        new_items = []
        api = twitter.Api(consumer_key=consumer_key,
                          consumer_secret=consumer_secret,
                          access_token_key=access_token_key,
                          access_token_secret=access_token_secret)
        try:
            screen_names = screen_names.split(',')
        except Exception as ex:
            raise IngestTwitterError.TwitterNoScreenNamesError(ex, provider)

        if not screen_names:
            raise IngestTwitterError.TwitterNoScreenNamesError(provider)
        for screen_name in screen_names:
            screen_name = screen_name.replace(' ', '')
            try:
                # hashtag search
                if screen_name.startswith('#'):
                    statuses = api.GetSearch(screen_name.lstrip('#'),
                                             count=status_count)
                # user search
                else:
                    statuses = api.GetUserTimeline(screen_name=screen_name,
                                                   count=status_count)
            except twitter.error.TwitterError as exc:
                if exc.message[0].get('code') == 34:
                    # that page does not exist
                    continue
                elif exc.message[0].get('code') == 32:
                    # invalid credentials
                    raise IngestTwitterError.TwitterLoginError(exc, provider)

            for status in statuses:
                d = parser.parse(status.created_at)
                guid_hash = hashlib.sha1(status.text.
                                         encode('utf8')).hexdigest()
                guid = generate_guid(type=GUID_TAG, id=guid_hash)
                headline = "%s: %s" % (status.user.screen_name, status.text)
                item = {}
                item['headline'] = headline
                item['type'] = 'text'
                item['guid'] = guid
                item['versioncreated'] = d
                item['firstcreated'] = d

                item['body_html'] = status.text
                # include URL on body
                urls = re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|'
                                  '[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
                                  status.text)
                if urls:
                    item['body_html'] += '<p><a href="%s"' \
                        ' target="_blank">%s</a></p>' % (urls[0], urls[0])

                # on hashtag search we don't want retweets
                if not (screen_name.startswith('#') and status.text
                        .startswith('RT ')):
                    new_items.append(item)
                    if status.media:
                        image_urls = []
                        for media_item in status.media:
                            if media_item.type in ['photo', 'animated',
                                                   'video']:
                                image_urls.append(media_item.media_url)
                        try:
                            # Eg can fail while fetching image
                            image_items = self._create_image_items(image_urls,
                                                                   item)
                            new_items.extend(image_items)
                            package_item = self._create_package(item,
                                                                image_items)
                            new_items.append(package_item)
                        except Exception as ex:
                            pass
        return [new_items]

    def _create_package(self, text_item, image_items):
        """
        Create a new content package from given content items.
        """
        package = {
            ITEM_TYPE: CONTENT_TYPE.COMPOSITE,
            'guid': generate_guid(type=GUID_TAG,
                                  id=text_item.get('guid') + '-package'),
            'versioncreated': text_item['versioncreated'],
            'firstcreated': text_item.get('firstcreated'),
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

    def _create_image_items(self, image_links, text_item):
        image_items = []

        for image_url in image_links:
            guid_hash = hashlib.sha1(image_url.encode('utf8')).hexdigest()
            img_item = {
                'guid': generate_guid(type=GUID_TAG,
                                      id=text_item.get('guid') +
                                      guid_hash + '-image'),
                ITEM_TYPE: CONTENT_TYPE.PICTURE,
                'versioncreated': text_item.get('versioncreated'),
                'firstcreated': text_item.get('firstcreated'),
                'headline': text_item.get('headline', ''),
                'renditions': {
                    'baseImage': {
                        'href': image_url
                    }
                }
            }
            image_items.append(img_item)

        return image_items


register_feeding_service(TwitterFeedingService.NAME, TwitterFeedingService(),
                         TwitterFeedingService.ERRORS)
