
# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license*.

import datetime
import email
import io
import logging
import re
from email.header import decode_header

import eve
from bs4 import BeautifulSoup, Comment, Doctype
from flask import current_app as app, json
from pytz import timezone

import superdesk
from superdesk import get_resource_service
from superdesk.errors import IngestEmailError
from superdesk.io import register_feed_parser
from superdesk.io.feed_parsers import EmailFeedParser
from superdesk.io.iptc import subject_codes
from superdesk.media.media_operations import process_file_from_stream
from superdesk.metadata.item import ITEM_TYPE, CONTENT_TYPE, GUID_TAG, SIGN_OFF, BYLINE
from superdesk.metadata.utils import generate_guid
from superdesk.users.errors import UserNotRegisteredException
from superdesk.utc import utcnow

logger = logging.getLogger(__name__)


email_regex = re.compile('^.*<(.*)>$')


class EMailRFC822FeedParser(EmailFeedParser):
    """
    Feed Parser which can parse if the feed is in RFC 822 format.
    """

    NAME = 'email_rfc822'

    def __init__(self):
        self.parser_app = app

    def can_parse(self, email_message):
        for response_part in email_message:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                return self.parse_header(msg['from']) != ''

        return False

    def parse(self, data, provider=None):
        config = provider.get('config', {})
        # If the channel is configured to process structured email generated from a google form
        if config.get('formatted', False):
            return self._parse_formatted_email(data, provider)
        try:
            new_items = []
            # create an item for the body text of the email
            # either text or html
            item = dict()
            item[ITEM_TYPE] = CONTENT_TYPE.TEXT
            item['versioncreated'] = utcnow()

            comp_item = None

            # a list to keep the references to the attachments
            refs = []

            html_body = None
            text_body = None

            for response_part in data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    item['headline'] = self.parse_header(msg['subject'])
                    field_from = self.parse_header(msg['from'])
                    item['original_source'] = field_from
                    try:
                        if email_regex.findall(field_from):
                            email_address = email_regex.findall(field_from)[0]
                            user = get_resource_service('users').get_user_by_email(email_address)
                            item['original_creator'] = user[eve.utils.config.ID_FIELD]
                    except UserNotRegisteredException:
                        pass
                    item['guid'] = msg['Message-ID']
                    date_tuple = email.utils.parsedate_tz(msg['Date'])
                    if date_tuple:
                        dt = datetime.datetime.utcfromtimestamp(
                            email.utils.mktime_tz(date_tuple))
                        dt = dt.replace(tzinfo=timezone('utc'))
                        item['firstcreated'] = dt

                    # this will loop through all the available multiparts in mail
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True)
                            try:
                                # if we don't know the charset just have a go!
                                if part.get_content_charset() is None:
                                    text_body = body.decode()
                                else:
                                    charset = part.get_content_charset()
                                    text_body = body.decode(charset)
                                continue
                            except Exception as ex:
                                logger.exception(
                                    "Exception parsing text body for {0} from {1}: {2}".format(item['headline'],
                                                                                               field_from, ex))
                                continue
                        if part.get_content_type() == "text/html":
                            body = part.get_payload(decode=True)
                            try:
                                if part.get_content_charset() is None:
                                    html_body = body.decode()
                                else:
                                    charset = part.get_content_charset()
                                    html_body = body.decode(charset)
                                html_body = self.safe_html(html_body)
                                continue
                            except Exception as ex:
                                logger.exception(
                                    "Exception parsing html body for {0} from {1}: {2}".format(item['headline'],
                                                                                               field_from, ex))
                                continue
                        if part.get_content_maintype() == 'multipart':
                            continue
                        if part.get('Content-Disposition') is None:
                            continue
                        # we are only going to pull off image attachments at this stage
                        if part.get_content_maintype() != 'image':
                            continue

                        fileName = part.get_filename()
                        if bool(fileName):
                            image = part.get_payload(decode=True)
                            content = io.BytesIO(image)
                            res = process_file_from_stream(content, part.get_content_type())
                            file_name, content_type, metadata = res
                            if content_type == 'image/gif' or content_type == 'image/png':
                                continue
                            content.seek(0)
                            image_id = self.parser_app.media.put(content, filename=fileName,
                                                                 content_type=content_type, metadata=metadata)
                            renditions = {'baseImage': {'href': image_id}}

                            # if we have not got a composite item then create one
                            if not comp_item:
                                comp_item = dict()
                                comp_item[ITEM_TYPE] = CONTENT_TYPE.COMPOSITE
                                comp_item['guid'] = generate_guid(type=GUID_TAG)
                                comp_item['versioncreated'] = utcnow()
                                comp_item['groups'] = []
                                comp_item['headline'] = item['headline']
                                comp_item['groups'] = []
                                comp_item['original_source'] = item['original_source']
                                if 'original_creator' in item:
                                    comp_item['original_creator'] = item['original_creator']

                                # create a reference to the item that stores the body of the email
                                item_ref = {'guid': item['guid'], 'residRef': item['guid'],
                                            'headline': item['headline'], 'location': 'ingest',
                                            'itemClass': 'icls:text', 'original_source': item['original_source']}
                                if 'original_creator' in item:
                                    item_ref['original_creator'] = item['original_creator']
                                refs.append(item_ref)

                            media_item = dict()
                            media_item['guid'] = generate_guid(type=GUID_TAG)
                            media_item['versioncreated'] = utcnow()
                            media_item[ITEM_TYPE] = CONTENT_TYPE.PICTURE
                            media_item['renditions'] = renditions
                            media_item['mimetype'] = content_type
                            media_item['filemeta'] = metadata
                            media_item['slugline'] = fileName
                            if text_body is not None:
                                media_item['body_html'] = text_body
                            media_item['headline'] = item['headline']
                            media_item['original_source'] = item['original_source']
                            if 'original_creator' in item:
                                media_item['original_creator'] = item['original_creator']
                            new_items.append(media_item)

                            # add a reference to this item in the composite item
                            media_ref = {'guid': media_item['guid'], 'residRef': media_item['guid'],
                                         'headline': fileName, 'location': 'ingest', 'itemClass': 'icls:picture',
                                         'original_source': item['original_source']}
                            if 'original_creator' in item:
                                media_ref['original_creator'] = item['original_creator']
                            refs.append(media_ref)

            if html_body is not None:
                item['body_html'] = html_body
            else:
                item['body_html'] = text_body
                item[ITEM_TYPE] = CONTENT_TYPE.PREFORMATTED

            # if there is composite item then add the main group and references
            if comp_item:
                grefs = {'refs': [{'idRef': 'main'}], 'id': 'root', 'role': 'grpRole:NEP'}
                comp_item['groups'].append(grefs)

                grefs = {'refs': refs, 'id': 'main', 'role': 'grpRole:Main'}
                comp_item['groups'].append(grefs)

                new_items.append(comp_item)

            new_items.append(item)
            return new_items
        except Exception as ex:
            raise IngestEmailError.emailParseError(ex, provider)

    def parse_header(self, field):
        try:
            hdr = decode_header(field)
            encoding = hdr[0][1]
            if encoding and hdr:
                parsed_field = hdr[0][0].decode(encoding)
            else:
                parsed_field = hdr[0][0]
        except:
            try:
                parsed_field = str(field)
            except:
                parsed_field = 'Unknown'
            pass
        return parsed_field

    # from http://chase-seibert.github.io/blog/2011/01/28/sanitize-html-with-beautiful-soup.html
    def safe_html(self, html):
        if not html:
            return None

        # remove these tags, complete with contents.
        blacklist = ["script", "style", "head"]

        whitelist = ["div", "span", "p", "br", "pre", "table", "tbody", "thead", "tr", "td", "a", "blockquote",
                     "ul", "li", "ol", "b", "em", "i", "strong", "u", "font"]

        try:
            # BeautifulSoup is catching out-of-order and unclosed tags, so markup
            # can't leak out of comments and break the rest of the page.
            soup = BeautifulSoup(html, "html.parser")
        except Exception as e:
            # special handling?
            raise e

        # remove the doctype declaration if present
        if isinstance(soup.contents[0], Doctype):
            soup.contents[0].extract()

        # now strip HTML we don't like.
        for tag in soup.findAll():
            if tag.name.lower() in blacklist:
                # blacklisted tags are removed in their entirety
                tag.extract()
            elif tag.name.lower() in whitelist:
                # tag is allowed. Make sure the attributes are allowed.
                attrs = dict(tag.attrs)
                for a in attrs:
                    if self._attr_name_whitelisted(a):
                        tag.attrs[a] = [self.safe_css(a, tag.attrs[a])]
                    else:
                        del tag.attrs[a]
            else:
                tag.replaceWithChildren()

        # scripts can be executed from comments in some cases
        comments = soup.findAll(text=lambda text: isinstance(text, Comment))
        for comment in comments:
            comment.extract()

        safe_html = str(soup)

        if safe_html == ", -":
            return None

        return safe_html.replace('</br>', '').replace('<br>', '<br/>')

    def _attr_name_whitelisted(self, attr_name):
        return attr_name.lower() in ["href", "style", "color", "size", "bgcolor", "border"]

    def safe_css(self, attr, css):
        if attr == "style":
            return re.sub("(width|height):[^;]+;", "", css)
        return css

    def _expand_category(self, item, mail_item):
        """
        Given a list of category names in the incoming email try to look them up to match category codes.
        If there is a subject associated with the category it will insert that into the item as well
        :param item:
        :param mail_item:
        :return: An item populated with category codes
        """
        anpa_categories = superdesk.get_resource_service('vocabularies').find_one(req=None,
                                                                                  _id='categories')
        if anpa_categories:
            for mail_category in mail_item.get('Category').split(','):
                for anpa_category in anpa_categories['items']:
                    if anpa_category['is_active'] is True \
                            and mail_category.strip().lower() == anpa_category['name'].lower():
                        if 'anpa_category' not in item:
                            item['anpa_category'] = list()
                        item['anpa_category'].append({'qcode': anpa_category['qcode']})
                        if anpa_category.get('subject'):
                            if 'subject' not in item:
                                item['subject'] = list()
                            item['subject'].append({'qcode': anpa_category.get('subject'),
                                                    'name': subject_codes[
                                                        anpa_category.get('subject')]})
                        break

    def _parse_formatted_email(self, data, provider):
        """
        Passed an email that was constructed as a notification from a google form submission it constructs an item.
        The google form submits to a google sheet, this sheet creates the email as a notification
        :param data:
        :param provider:
        :return: A list of 1 item
        """
        try:
            item = dict()
            item[ITEM_TYPE] = CONTENT_TYPE.TEXT
            item['versioncreated'] = utcnow()
            for response_part in data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    # Check that the subject line matches what we expect, ignore it if not
                    if self.parse_header(msg['subject']) != 'Formatted Editorial Story':
                        return []

                    item['guid'] = msg['Message-ID']
                    date_tuple = email.utils.parsedate_tz(msg['Date'])
                    if date_tuple:
                        dt = datetime.datetime.utcfromtimestamp(
                            email.utils.mktime_tz(date_tuple))
                        dt = dt.replace(tzinfo=timezone('utc'))
                        item['firstcreated'] = dt

                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True)
                            # if we don't know the charset just have a go!
                            if part.get_content_charset() is None:
                                json_str = body.decode().replace('\r\n', '').replace('  ', ' ')
                            else:
                                charset = part.get_content_charset()
                                json_str = body.decode(charset).replace('\r\n', '').replace('  ', ' ')

                            mail_item = dict((k, v[0]) for k, v in json.loads(json_str).items())

                            self._expand_category(item, mail_item)

                            item['original_source'] = mail_item.get('Username')
                            item['headline'] = mail_item.get('Headline')
                            item['abstract'] = mail_item.get('Abstract')
                            item['slugline'] = mail_item.get('Slugline')
                            item['body_html'] = mail_item.get('Body').replace('\n', '<br />')

                            if mail_item.get('Priority') != '':
                                item['priority'] = int(mail_item.get('Priority'))
                            if mail_item.get('Urgency') != '':
                                item['urgency'] = int(mail_item.get('Urgency'))

                            # We expect the username passed corresponds to a superdesk user
                            query = {'email': re.compile('^{}$'.format(mail_item.get('Username')), re.IGNORECASE)}
                            user = superdesk.get_resource_service('users').find_one(req=None, **query)
                            if not user:
                                logger.error('Failed to find user for email {}'.format(mail_item.get('Username')))
                                raise UserNotRegisteredException()
                            item['original_creator'] = user.get('_id')
                            item['byline'] = user.get(BYLINE, user.get('display_name'))
                            item[SIGN_OFF] = user.get(SIGN_OFF)

                            # attempt to match the given desk name against the defined desks
                            desk = superdesk.get_resource_service('desks').find_one(
                                req=None, name=mail_item.get('Desk'))
                            if desk:
                                item['task'] = {'desk': desk.get('_id'), 'stage': desk.get('incoming_stage')}
                            break
            return [item]
        except Exception as ex:
            raise IngestEmailError.emailParseError(ex, provider)


register_feed_parser(EMailRFC822FeedParser.NAME, EMailRFC822FeedParser())
