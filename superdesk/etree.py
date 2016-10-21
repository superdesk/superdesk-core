
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
import bs4
import xml.etree.ElementTree as etree  # noqa
from xml.etree.ElementTree import ParseError  # noqa

inline_elements = set([
    'a',
    'b',
    'i',
    'em',
    'img',
    'sub',
    'sup',
    'abbr',
    'bold',
    'span',
    'cite',
    'code',
    'small',
    'label',
    'script',
    'strong',
    'object',
])


_word_pattern = re.compile('.*[\w\d].*')


def is_word(word):
    """Test if given word is word - contains any word character.

    :param word: word string
    """
    return word and _word_pattern.match(word)


def get_text_word_count(text):
    """Get word count for given plain text.

    :param text: text string
    """
    return len([word for word in text.split() if is_word(word)])


def get_text(html):
    """Get plain text version of HTML element

    if the HTML string can't be parsed, it will be returned unchanged
    :param html: html string to convert to plain text
    """
    try:
        root = etree.fromstringlist('<doc>{0}</doc>'.format(html))
        text = etree.tostring(root, encoding='unicode', method='text')
        return text
    except ParseError:
        return html


def get_word_count(html):
    """Get word count for given html.

    :param html: html string to count
    """
    soup = bs4.BeautifulSoup(html.replace('<br>', ' ').replace('<hr>', ' '), 'html.parser')

    # first run to filter out inlines
    for elem in soup.find_all():
        if elem.name in inline_elements:  # ignore inline elements
            elem.unwrap()

    # re-parse without inline, it will merge sibling text nodes
    soup = bs4.BeautifulSoup(str(soup), 'html.parser')
    text = ' '.join(soup.find_all(text=True))
    return get_text_word_count(text)


def get_char_count(html):
    """Get character count for given html.

    :param html: html string to count
    """
    return len(get_text(html))
