
# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2017 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import re
import regex
import logging
from lxml import etree  # noqa
from superdesk import etree as sd_etree
from lxml import html as lxml_html
from lxml.html import clean
from flask import current_app as app
import chardet

logger = logging.getLogger(__name__)


# KEEP CHANGES IN SYNC WITH CLIENT FUNCTION `countWords`
# regex is used instead re to support unicode letter matching with \p{L}
def get_text_word_count(text):
    """Get word count for given plain text.

    :param str text: text string
    :return int: word count
    """

    flags = regex.MULTILINE | regex.UNICODE
    initial_text_trimmed = text.strip()

    if len(initial_text_trimmed) < 1:
        return 0

    r0 = get_text(initial_text_trimmed, space_on_elements=True)

    r1 = regex.sub(r'\n', ' ', r0, flags=flags)

    # Remove spaces between two numbers
    # 1 000 000 000 -> 1000000000
    r2 = regex.sub(r'([0-9]) ([0-9])', '\\1\\2', r1, flags=flags)

    # remove anything that is not a unicode letter, a space or a number
    r3 = regex.sub(r'[^\p{L} 0-9]', '', r2, flags=flags)

    # replace two or more spaces with one space
    r4 = regex.sub(r' {2,}', ' ', r3, flags=flags)

    result = len(r4.strip().split(" "))

    return result


def get_text(markup, content='xml', lf_on_block=False, space_on_elements=False, space=' '):
    """Get plain text version of (X)HTML or other XML element

    if the markup can't be parsed, it will be returned unchanged
    :param str markup: string to convert to plain text
    :param str content: 'xml' or 'html', as in parse_html
    :param bool lf_on_block: if True, add a line feed on block elements' tail
    :param bool space_on_elements: if True, add a space on each element's tail
        mainly used to count words with non HTML markup
    :param str space: space string which is used when `space_on_elements` is enabled
    :return str: plain text version of markup
    """
    try:
        root = sd_etree.parse_html(
            markup,
            content=content,
            lf_on_block=lf_on_block,
            space_on_elements=space_on_elements,
            space=space
        )
        text = etree.tostring(root, encoding='unicode', method='text')
        return text
    except etree.ParseError:
        return markup


def get_word_count(markup, no_html=False):
    """Get word count for given html.

    :param str markup: xhtml (or other xml) markup
    :param bool no_html: set to True if xml param is not (X)HTML
        if True, a space will be added after each element to separate words.
        This avoid to have construct like <hl2>word</hl2><p>another</p> (like in NITF)
        being counted as one word.
    :return int: count of words inside the text
    """
    if no_html:
        return get_text_word_count(get_text(markup, content='xml', space_on_elements=True))
    else:
        return get_text_word_count(get_text(markup, content='html', lf_on_block=True))


def update_word_count(update, original=None):
    """Update word count if there was change in content.

    :param update: created/updated document
    :param original: original document if updated
    """
    if update.get('body_html'):
        update.setdefault('word_count', get_word_count(update.get('body_html')))
    else:
        # If the body is removed then set the count to zero
        if original and 'word_count' in original and 'body_html' in update:
            update['word_count'] = 0


def get_char_count(html):
    """Get character count for given html.

    :param html: html string to count
    :return int: count of chars inside the text
    """
    return len(get_text(html))


def get_par_count(html):
    try:
        elem = sd_etree.parse_html(html, content='html')
        return len([
            p for p in elem.iterfind('.//p')
            if p.text and len(p.text.strip()) > 0
        ])
    except ValueError as e:
        logger.warning(e)

    logger.warning('Failed to determine paragraph count from html: {}.'.format(html))
    return 0


def get_reading_time(html, word_count=None, language=None):
    """Get estimanted number of minutes to read a text

    Check https://dev.sourcefabric.org/browse/SDFID-118 for details

    :param str html: html content
    :param int word_count: number of words in the text
    :param str language: language of the text
    :return int: estimated number of minute to read the text
    """
    if language and language.startswith('ja'):
        return round(len(re.sub(r'[\s]', '', get_text(html))) / app.config['JAPANESE_CHARACTERS_PER_MINUTE'])
    if not word_count:
        word_count = get_word_count(html)
    reading_time_float = word_count / 250
    reading_time_minutes = int(reading_time_float)
    reading_time_rem_sec = int((reading_time_float - reading_time_minutes) * 60)
    if reading_time_rem_sec >= 30:
        reading_time_minutes += 1
    return reading_time_minutes


def sanitize_html(html):
    """Sanitize HTML

    :param str html: unsafe HTML markup
    :return str: sanitized HTML
    """
    if not html:
        return ""

    blacklist = ["script", "style", "head"]

    root_elem = lxml_html.fromstring(html)
    cleaner = clean.Cleaner(
        add_nofollow=False,
        kill_tags=blacklist
    )
    cleaned_xhtml = cleaner.clean_html(root_elem)

    safe_html = etree.tostring(cleaned_xhtml, encoding="unicode")

    # the following code is legacy (pre-lxml)
    if safe_html == ", -":
        return ""

    return safe_html


def decode(bytes_str):
    """Decode bytes value

    try to decode using UTF-8, or to detect encoding. Will ignore bad chars as a last resort
    @return (str): decoded string
    """
    try:
        return bytes_str.decode('utf-8')
    except UnicodeDecodeError:
        try:
            return bytes_str.decode(chardet.detect(bytes_str)['encoding'])
        except Exception:
            return bytes_str.decode('utf-8', 'ignore')
