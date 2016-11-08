# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import json
import superdesk
from superdesk.publish.formatters import Formatter
from superdesk.metadata.item import ITEM_TYPE, CONTENT_TYPE, FORMAT, FORMATS
from flask import render_template
from copy import deepcopy
from bs4 import BeautifulSoup, NavigableString
from superdesk.errors import FormatterError


class EmailFormatter(Formatter):
    """Superdesk Email formatter.

    - Does not support any media output, it's for text items only.

    It uses templates to render items, those can be overriden to customize the output:

    - ``email_article_subject.txt``
        email subject

    - ``email_article_body.txt``
        email text content

    - ``email_article_body.html``
        email html content

    It gets ``article`` with item data, can be used in templates like::

       <strong>{{ article.headline }}</strong>

    """

    def format(self, article, subscriber, codes=None):
        formatted_article = deepcopy(article)
        pub_seq_num = superdesk.get_resource_service('subscribers').generate_sequence_number(subscriber)
        doc = {}
        try:
            # If there is a dateline inject it into the body
            if formatted_article.get(FORMAT) == FORMATS.HTML and formatted_article.get('dateline', {}).get('text'):
                soup = BeautifulSoup(formatted_article.get('body_html'), "html.parser")
                ptag = soup.find('p')
                if ptag is not None:
                    ptag.insert(0, NavigableString('{} '.format(formatted_article.get('dateline').get('text'))))
                    formatted_article['body_html'] = str(soup)
                doc['message_html'] = render_template('email_article_body.html', article=formatted_article)
            else:
                doc['message_html'] = None
            doc['message_text'] = render_template('email_article_body.txt', article=formatted_article)
            doc['message_subject'] = render_template('email_article_subject.txt', article=formatted_article)
        except Exception as ex:
            raise FormatterError.EmailFormatterError(ex, FormatterError)
        return [(pub_seq_num, json.dumps(doc))]

    def can_format(self, format_type, article):
        return format_type.lower() == 'email' and article[ITEM_TYPE] == CONTENT_TYPE.TEXT
