
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
from lxml import etree  # noqa
from lxml.etree import ParseError  # noqa
from lxml import html as lxml_html
from lxml.html import clean


# This pattern matches http(s) links, numbers (1.000.000 or 1,000,000 or 1 000 000), regulars words,
# compound words (e.g. "two-done") or abbreviation (e.g. D.C.)
WORD_PATTERN = re.compile(r'https?:[^ ]*|([0-9]+[,. ]?)+|([\w]\.)+|[\w][\w-]*')

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


def parse_html(html, content='xml', lf_on_block=False, space_on_elements=False):
    """Parse element and return etreeElement

    <div> element is added around the HTML
    recovery is used in case of bad markup
    :param str html: HTML markup
    :param str content: use 'xml' for XHTML or non html XML, and 'html' for HTML or if you are unsure
    :param bool lf_on_block: if True, add a line feed on block elements' tail
    :param bool space_on_elements: if True, add a space on each element's tail
        mainly used to count words with non HTML markup
    :return etree.Element: parsed element
    """
    if not isinstance(html, str):
        raise ValueError("a string is expected")
    if not html:
        return etree.Element('div')

    if content == 'xml':
        # to preserve 'carriage return' otherwise it gets stripped.
        html = html.replace('\r', '&#13;')
        parser = etree.XMLParser(recover=True, remove_blank_text=True)
        root = etree.fromstring("<div>" + html + "</div>", parser)
    elif content == 'html':
        parser = etree.HTMLParser(recover=True, remove_blank_text=True)
        root = etree.fromstring(html, parser)
        if root is None:
            root = etree.Element('div')
        else:
            root = root.find('body')
            root.tag = 'div'
    else:
        raise ValueError('invalid content: {}'.format(content))
    if lf_on_block:
        for elem in root.iterfind('.//'):
            if elem.tag in BLOCK_ELEMENTS:
                elem.tail = (elem.tail or '') + '\n'
    if space_on_elements:
        for elem in root.iterfind('.//'):
            elem.tail = (elem.tail or '') + ' '
    return root


def get_text_word_count(text):
    """Get word count for given plain text.

    :param str text: text string
    :return int: word count
    """
    return sum(1 for word in WORD_PATTERN.finditer(text))


def get_text(markup, content='xml', lf_on_block=False, space_on_elements=False):
    """Get plain text version of (X)HTML or other XML element

    if the markup can't be parsed, it will be returned unchanged
    :param str markup: string to convert to plain text
    :param str content: 'xml' or 'html', as in parse_html
    :param bool lf_on_block: if True, add a line feed on block elements' tail
    :param bool space_on_elements: if True, add a space on each element's tail
        mainly used to count words with non HTML markup
    :return str: plain text version of markup
    """
    try:
        root = parse_html(markup, content=content, lf_on_block=lf_on_block, space_on_elements=space_on_elements)
        text = etree.tostring(root, encoding='unicode', method='text')
        return text
    except ParseError:
        return markup


def to_string(elem, encoding="unicode", method="xml", remove_root_div=True):
    """Convert Element to string

    :param etree.Element elem: element to convert
    :param str encoding: encoding to use (same as for etree.tostring)
    :param str method: method to use (same as for etree.tostring)
    :param bool remove_root_dir: if True remove surrounding <div> which is added by parse_html
    :return str: converted element
    """
    string = etree.tostring(elem, encoding=encoding, method=method)
    if remove_root_div:
        if encoding == "unicode":
            div_start = "<div>"
            div_end = "</div>"
        else:
            div_start = b"<div>"
            div_end = b"</div>"
        if string.startswith(div_start) and string.endswith(div_end):
            return string[len(div_start):-len(div_end)]
    return string


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


def get_char_count(html):
    """Get character count for given html.

    :param html: html string to count
    :return int: count of chars inside the text
    """
    return len(get_text(html))


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
