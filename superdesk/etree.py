
# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

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

# from https://developer.mozilla.org/en-US/docs/Web/HTML/Block-level_elements
BLOCK_ELEMENTS = (
    "address",
    "article",
    "aside",
    "blockquote",
    "br",
    "canvas",
    "dd",
    "div",
    "dl",
    "fieldset",
    "figcaption",
    "figure",
    "footer",
    "form",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "header",
    "hgroup",
    "hr",
    "li",
    "main",
    "nav",
    "noscript",
    "ol",
    "output",
    "p",
    "pre",
    "section",
    "table",
    "tfoot",
    "ul",
    "video")

# from https://www.w3.org/TR/html/syntax.html#void-elements
VOID_ELEMENTS = (
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "keygen",
    "link",
    "menuitem",
    "meta",
    "param",
    "source",
    "track",
    "wbr")


def fix_html_void_elements(element):
    """Use self-closing elements for HTML void elements, and start/end pairs otherwise

    :param element: Element to fix
    :type element: lxml.etree.Element
    :return: fixed Element
    """
    # we want self closing for HTML void elemends and start/end tags otherwise
    # so we set element.text to None for void ones, and empty string otherwise
    for e in element.xpath("//*[not(node())]"):
        e.text = None if e.tag in VOID_ELEMENTS else ''
    return element


def get_text_word_count(text):
    """Get word count for given plain text.

    :param text: text string
    """
    return len(text.split())


def get_text(html, content='xml', lf_on_block=False):
    """Get plain text version of HTML element

    if the HTML string can't be parsed, it will be returned unchanged
    :param html: html string to convert to plain text
    :param str content: 'xml' or 'html'
    :param bool lf_on_block: if True, add a line feed on block elements' tail
    """
    try:
        if content == 'html':
            # FIXME: this is a fragile way of handling HTML, it will be properly fixed
            #        when lxml patch will be used
            html = html.replace('<br>', '<br/>').replace('</br>', '').replace('<hr>', ' ')
        root = etree.fromstringlist('<doc>{0}</doc>'.format(html))
        if lf_on_block:
            for elem in root.iterfind('.//'):
                if elem.tag in BLOCK_ELEMENTS:
                    elem.tail = (elem.tail or '') + '\n'
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
