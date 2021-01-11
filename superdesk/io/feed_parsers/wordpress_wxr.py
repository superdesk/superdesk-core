# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import logging
from superdesk.io.registry import register_feed_parser
from superdesk.io.feed_parsers import XMLFeedParser
from superdesk.utc import utcnow
from email.utils import parsedate_to_datetime
from superdesk import etree as sd_etree
from superdesk.metadata.item import ITEM_TYPE, CONTENT_TYPE, GUID_FIELD
from superdesk.media.renditions import update_renditions
from xml.sax.saxutils import quoteattr
from lxml import etree
from collections import OrderedDict

logger = logging.getLogger(__name__)
nsmap = {
    "excerpt": "http://wordpress.org/export/1.2/excerpt/",
    "content": "http://purl.org/rss/1.0/modules/content/",
    "wfw": "http://wellformedweb.org/CommentAPI/",
    "dc": "http://purl.org/dc/elements/1.1/",
    "wp": "http://wordpress.org/export/1.2/",
}
embed_TPL = 'EMBED {} Image {{id: "{}"}}'

BLOCK_WHITELIST = {
    "<h",  # hr + h[1..9]
    "<br",
    "<p",
    "<div",
    "<iframe",
    "<ul",
    "<ol",
    "<li",
    "<table",
    "</",
}


def is_block_elem(line):
    text = line.lstrip()
    for block in BLOCK_WHITELIST:
        if text.startswith(block):
            return True
    return False


class WPWXRFeedParser(XMLFeedParser):
    """
    Feed Parser for Wordpress' WXR format
    """

    NAME = "wpwxr"

    label = "Wordpress WXR parser"

    def __init__(self):
        super().__init__()
        # we use OrderedDict to have control on parsing order
        self.default_mapping = OrderedDict(
            [
                ("guid", "guid"),
                ("item_id", "guid"),
                ("_current_version", lambda _: 1),
                ("versioncreated", lambda _: utcnow()),
                ("firstpublished", {"xpath": "pubDate/text()", "filter": parsedate_to_datetime}),
                ("author", "dc:creator"),
                ("headline", "title"),
                # featuremedia must called before body_html, so thumbnail is used
                # in priority as feature media (else body_html would use first image
                # as feature media).
                ("featuremedia", self.parse_thumbnail),
                # images are handled in body_hook
                ("body_html", {"xpath": "content:encoded", "key_hook": self.body_hook}),
                ("keywords", {"xpath": 'category[@domain="post_tag"]', "list": True}),
                (
                    "anpa_category",
                    {
                        "xpath": 'category[@domain="category"]/text()',
                        "list": True,
                        "filter": lambda cat: {"qcode": cat, "name": cat},
                    },
                ),
                ("attachments", {"xpath": "wp:attachment_url", "list": True, "key_hook": self.attachments_hook}),
            ]
        )

    def can_parse(self, xml):
        return xml.tag == "rss"

    def parse(self, xml, provider=None):
        return list(self.parse_items(xml))

    def parse_items(self, xml):
        for item_xml in xml.findall("channel/item"):
            try:
                post_type = item_xml.xpath("wp:post_type", namespaces=nsmap)[0].text
            except IndexError:
                pass
            else:
                if post_type and post_type != "post":
                    # we don't want to parse attachments
                    continue
            yield self.parse_item(item_xml)

    def parse_item(self, item_xml):
        item = {}
        self.do_mapping(item, item_xml, namespaces=nsmap)
        if "associations" in item:
            for _, data in item["associations"].items():
                if data is None:
                    continue
                # these 3 fields are mandatory in default setup
                # we use a space for that to avoid issue when publishing
                data.setdefault("headline", item["headline"])
                data.setdefault("alt_text", " ")
                data.setdefault("description_text", " ")
            if (
                len(item["associations"]) == 1
                and not item["body_html"]
                and item.get("associations", {}).get("featuremedia")
            ):
                # if the item only contains a feature media, we convert it to picture
                featuremedia = item["associations"]["featuremedia"]
                item["renditions"] = featuremedia["renditions"]
                item[ITEM_TYPE] = featuremedia[ITEM_TYPE]
                item["alt_text"] = item["headline"]
                item["media"] = item["renditions"]["original"]["media"]
                item["mimetype"] = item["renditions"]["original"]["mimetype"]
                del item["associations"]
        return item

    def check_url(self, url):
        """Check URL and add protocol in case of relative URL

        :param url: found URL
        :return unicode: HTTP(s) URL
        :raises ValueError: the URL is invlalid
        """
        if url is None:
            raise ValueError("No URL found")
        url = url.strip()
        if not url:
            raise ValueError("URL is empty")
        if url.startswith("//"):
            # if we have a protocol relative URL, we use https
            url = "https:" + url
        if not url.startswith("http"):
            raise ValueError("Url is not HTTP(s)")
        return url

    def _add_image(self, item, url):
        associations = item.setdefault("associations", {})
        association = {
            ITEM_TYPE: CONTENT_TYPE.PICTURE,
            "ingest_provider": self.NAME,
            GUID_FIELD: url,
        }
        update_renditions(association, url, None)

        # we use featuremedia for the first image, then embeddedX
        if "featuremedia" not in associations:
            key = "featuremedia"
        else:
            key = "embedded" + str(len(associations) - 1)

        associations[key] = association
        return key, association

    def parse_thumbnail(self, item_elt, item):
        """Check for _thumbnail_id meta_key, and use its attachment as feature media

        If the key is found, the linked item is looked for, and its attachment_url is used as feature media
        """
        thumbnail_elt = item_elt.xpath('wp:postmeta/wp:meta_key[text()="_thumbnail_id"]', namespaces=nsmap)
        if not thumbnail_elt:
            return
        thumbnail_elt = thumbnail_elt[0]

        try:
            post_id = thumbnail_elt.xpath("../wp:meta_value/text()", namespaces=nsmap)[0].strip()
            if not post_id:
                raise IndexError
        except IndexError:
            logger.warning(
                "invalid post_id, ignoring: {elt}".format(elt=sd_etree.to_string(thumbnail_elt.xpath("..")[0]))
            )
            return
        try:
            if '"' in post_id:
                raise ValueError('post id should not contain " (double quote)')
            post_id_elt = item_elt.xpath('/rss/channel/item/wp:post_id[text()="{}"]'.format(post_id), namespaces=nsmap)[
                0
            ]
            att_item_elt = post_id_elt.getparent()
            url = att_item_elt.xpath("wp:attachment_url", namespaces=nsmap)[0].text.strip()
            url = self.check_url(url)
        except (IndexError, ValueError) as e:
            logger.warning(
                "Can't find attachement URL, ignoring: {e}\n{elt}".format(
                    e=e, elt=sd_etree.to_string(thumbnail_elt.getparent())
                )
            )
            return
        try:
            key, media_data = self._add_image(item, url)
        except Exception as e:
            logger.error(e)
            return

        for key, elt_names in (("description_text", ("description", "title")), ("alt_text", ("title",))):
            for elt_name in elt_names:
                elt = att_item_elt.find(elt_name)
                if elt is not None and elt.text:
                    media_data[key] = elt.text
                    break
            else:
                media_data[key] = ""

    def body_hook(self, item, html):
        """Copy content to body_html

        if img are found in the content, they are uploaded.
        First image is used as feature media, then there are embeds
        """
        # we need to convert CRLF to <p>
        # cf. SDTS-22
        html = html.replace("&#13;", "\r")
        splitted = html.split("\r\n")
        if len(splitted) == 1 and "<p>" not in html:
            splitted = html.split("\n")
        if len(splitted) > 1:
            html = "".join(["<p>{}</p>".format(s) if not is_block_elem(s) else s for s in splitted if s.strip()])

        if "img" in html:
            content = sd_etree.parse_html(html, "html")
            for img in content.xpath("//img"):
                try:
                    src = self.check_url(img.get("src"))
                except ValueError:
                    logger.warning("Can't fetch image: {elt}".format(elt=sd_etree.to_string(img)))
                    continue
                try:
                    key, media_data = self._add_image(item, src)
                except Exception as e:
                    logger.error(e)
                    img.getparent().remove(img)
                    continue
                url = media_data["renditions"]["original"]["href"]
                img.set("src", url)
                if key == "featuremedia":
                    # no need to embed the image for featuremedia
                    continue
                embed_start = etree.Comment(embed_TPL.format("START", key))
                embed_end = etree.Comment(embed_TPL.format("END", key))
                img.addprevious(embed_start)
                img.addnext(embed_end)

            content = sd_etree.fix_html_void_elements(content)
            html = sd_etree.to_string(content, encoding="unicode", method="xml")

        item["body_html"] = html

    def attachments_hook(self, item, attachments):
        """Attachment are parsed at the end

        if it's the first image found, it's used as feature media
        else it's used as embed and put at the end of body_html
        """
        for url in attachments:
            try:
                key, media_data = self._add_image(item, url)
            except Exception as e:
                logger.error(e)
                continue
            if key == "featuremedia":
                # no need to embed the image for featuremedia
                continue
            embed_start = "<!--" + embed_TPL.format("START", key) + "-->"
            embed_end = "<!--" + embed_TPL.format("END", key) + "-->"
            new_url = media_data["renditions"]["original"]["href"]
            img = '<img src={src} height="{height}" width="{width}">'.format(
                src=quoteattr(new_url),
                height=media_data["renditions"]["original"]["height"],
                width=media_data["renditions"]["original"]["width"],
            )
            item["body_html"] += "<div>" + embed_start + img + embed_end + "</div>"


register_feed_parser(WPWXRFeedParser.NAME, WPWXRFeedParser())
