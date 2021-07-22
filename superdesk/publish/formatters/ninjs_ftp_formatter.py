# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


from .ninjs_formatter import NINJSFormatter
from superdesk.media.renditions import get_rendition_file_name
from lxml import html as lxml_html
from superdesk.etree import to_string
import logging
import re

logger = logging.getLogger(__name__)


class FTPNinjsFormatter(NINJSFormatter):
    def __init__(self):
        super().__init__()
        self.format_type = "ftp ninjs"
        self.internal_renditions = []

    def _get_source_ref(self, marker, ninjs):
        try:
            return ninjs.get("associations").get(marker).get("renditions").get("original").get("href")
        except Exception:
            logger.warning(
                "href not found for the original in FTP NINJS formatter, ensure the formatter has it enabled"
            )
            return None

    def _transform_to_ninjs(self, article, subscriber, recursive=True):
        """
        Re-wire that href's in the document to be relative to the destination FTP server root, it expects the
        destination to be an FTP server
        :param article:
        :param subscriber:
        :param recursive:
        :return:
        """

        include_original = subscriber.get("destinations")[0].get("config").get("include_original", False)
        if include_original:
            self.internal_renditions = ["original"]

        ninjs = super()._transform_to_ninjs(article, subscriber, recursive)

        # Get the path that the renditions will be pushed to
        path = subscriber.get("destinations")[0].get("config").get("associated_path")

        if path:
            renditions = ninjs.get("renditions")
            if renditions:
                for name, rendition in renditions.items():
                    rendition["href"] = (
                        "/"
                        + path.lstrip("/")
                        + ("/" if not path.endswith("/") else "")
                        + get_rendition_file_name(rendition)
                    )

        if article.get("type", "") == "text":
            # Find any embeded image references in the body_html and re-wire the img src reference and insert an id
            html_updated = False
            root_elem = lxml_html.fromstring(ninjs.get("body_html"))
            # Scan any comments for embed markers
            comments = root_elem.xpath("//comment()")
            for comment in comments:
                if "EMBED START Image" in comment.text:
                    regex = r"<!-- EMBED START Image {id: \"editor_([0:9]+)"
                    m = re.search(regex, ninjs.get("body_html", ""))
                    # Assumes the sibling of the Embed Image comment is the figure tag containing the image
                    figureElem = comment.getnext()
                    if figureElem is not None and figureElem.tag == "figure":
                        imgElem = figureElem.find("./img")
                        if imgElem is not None and m and m.group(1):
                            embed_id = "editor_" + m.group(1)
                            imgElem.attrib["id"] = embed_id
                            src = self._get_source_ref(embed_id, ninjs)
                            if src:
                                imgElem.attrib["src"] = src
                            html_updated = True
            if html_updated:
                ninjs["body_html"] = to_string(root_elem, method="html")
        return ninjs
