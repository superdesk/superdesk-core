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
from superdesk.errors import FormatterError
from superdesk import etree as sd_etree


class EmailFormatter(Formatter):
    """Superdesk Email formatter.

    Feature media renditions are passed on to the transmit service, which if configured will attach the media to
    the email.

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

    def _inject_dateline(self, formatted_article):
        """Inject dateline in article's body_html"""
        body_html_elem = sd_etree.parse_html(formatted_article.get('body_html', '<p> </p>'))
        ptag = body_html_elem.find('.//p')
        if ptag is not None:
            ptag.text = formatted_article['dateline']['text'] + ' ' + (ptag.text or '')
            formatted_article['body_html'] = sd_etree.to_string(body_html_elem)

    def format(self, article, subscriber, codes=None):
        formatted_article = deepcopy(article)
        pub_seq_num = superdesk.get_resource_service('subscribers').generate_sequence_number(subscriber)
        doc = {}
        try:
            if formatted_article.get(FORMAT) == FORMATS.HTML:
                if formatted_article.get('dateline', {}).get('text'):
                    # If there is a dateline inject it into the body
                    self._inject_dateline(formatted_article)
                doc['message_html'] = render_template('email_article_body.html', article=formatted_article)
            else:
                doc['message_html'] = None
            doc['message_text'] = render_template('email_article_body.txt', article=formatted_article)
            doc['message_subject'] = render_template('email_article_subject.txt', article=formatted_article)
            doc['renditions'] = ((formatted_article.get('associations', {}) or {}).get('featuremedia', {}) or {}).get(
                'renditions')
        except Exception as ex:
            raise FormatterError.EmailFormatterError(ex, FormatterError)
        return [(pub_seq_num, json.dumps(doc))]

    def can_format(self, format_type, article):
        return format_type.lower() == 'email' and article[ITEM_TYPE] == CONTENT_TYPE.TEXT
