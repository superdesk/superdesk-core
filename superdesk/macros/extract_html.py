# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2016 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk import etree as sd_etree
from lxml import etree
from flask_babel import lazy_gettext


def extract_html_macro(item, **kwargs):
    """Delete from body_html all html tags except links"""
    if "body_html" not in item:
        return None

    root = sd_etree.parse_html(item["body_html"], content="html")

    links = {}
    count = 0
    # extract all links and add them to a dictionary with a unique
    # generated key for every link
    for a in root.findall(".//a"):
        links["__##link" + str(count) + "##__"] = etree.tostring(a, encoding="unicode")
        count = count + 1

    # replace all text links with the generated keys
    # regenerate html back from root in order to avoid issues
    # on link replacements where are used text links generated from root
    body_html = etree.tostring(root, encoding="unicode")
    for link in links:
        body_html = body_html.replace(links[link], link)
    body_html = body_html.replace("<p>", "__##br##__")
    body_html = body_html.replace("</p>", "__##br##__")
    body_html = body_html.replace("<br/>", "__##br##__")

    # extract text from the html that don't contains any link,
    # it just contains link keys that are not affected by text extraction
    # because they are already text
    root = sd_etree.parse_html(body_html, content="html")
    body_html = etree.tostring(root, encoding="unicode", method="text")

    # in extracted text replace the link keys with links
    for link in links:
        body_html = body_html.replace(link, links[link])

    body_html = body_html.replace("\n", "__##br##__")
    list_paragraph = body_html.split("__##br##__")
    item["body_html"] = "".join("<p>" + p + "</p>" for p in list_paragraph if p and p.strip())
    return item


name = "Extract Html Macro"
label = lazy_gettext("Extract Html Macro")
callback = extract_html_macro
access_type = "frontend"
action_type = "direct"
