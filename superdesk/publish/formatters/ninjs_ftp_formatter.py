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
from flask import current_app as app
from superdesk.media.renditions import get_rendition_file_name
from superdesk import get_resource_service
from superdesk.editor_utils import get_content_state_fields, Editor3Content, DraftJSHTMLExporter
from superdesk.media.renditions import get_renditions_spec
from draftjs_exporter.dom import DOM
from copy import deepcopy
from textwrap import dedent
import logging

logger = logging.getLogger(__name__)


class FTPNinjsFormatter(NINJSFormatter):
    name = "NINJS FTP"
    type = "ftp ninjs"

    def __init__(self):
        super().__init__()
        self.internal_renditions = []
        self.path = None

    def _transform_to_ninjs(self, article, subscriber, recursive=True):
        """
        Re-wire that href's in the document to be relative to the destination FTP server root, it expects the
        destination to be an FTP server
        :param article:
        :param subscriber:
        :param recursive:
        :return:
        """
        # Get the path that the renditions will be pushed to
        self.path = subscriber.get("destinations")[0].get("config").get("associated_path")
        include_original = subscriber.get("destinations")[0].get("config").get("include_original", False)
        if include_original:
            self.internal_renditions = ["original"]

        formatted_article = deepcopy(article)

        if article.get("type") == "text" and recursive:
            self.apply_product_filtering_to_associations(formatted_article, subscriber)

        ninjs = super()._transform_to_ninjs(formatted_article, subscriber, recursive)

        renditions = ninjs.get("renditions")
        if renditions:
            for name, rendition in renditions.items():
                rendition["href"] = (
                    self.path.lstrip("/")
                    + ("/" if not self.path.endswith("/") and self.path else "")
                    + get_rendition_file_name(rendition)
                )

        return ninjs

    def apply_product_filtering_to_associations(self, article, subscriber):
        """
        Remove the embedded items from the article that the subscriber has no matching product for.
        :param article:
        :param subscriber:
        :return:
        """
        if not app.config["EMBED_PRODUCT_FILTERING"]:
            return

        remove_keys = []
        permitted_products = set(subscriber["products"])

        for key, item in article.get("associations", {}).items():
            if key.startswith("editor_"):
                result = get_resource_service("product_tests").test_products(item, lookup=None)
                matching_products = set(p["product_id"] for p in result if p.get("matched", False))
                if not matching_products.intersection(permitted_products):
                    remove_keys.append(key)

        self.remove_embeds(article, remove_keys)

    def remove_embeds(self, article, remove_keys):
        """
        Removes the nominated embeds from the draftjs state and regenerates the HTML.
        :param article:
        :param remove_keys
        :return:
        """

        to_remove = [k.lstrip("editor_") for k in remove_keys]

        def not_embed(block):
            if block.type.lower() == "atomic":
                bk = [e.key for e in block.entities if e.key in to_remove]
                if bk:
                    return False
            return True

        fields = get_content_state_fields(article)
        for field in fields:
            self.filter_blocks(article, field, not_embed)

        for key in remove_keys:
            article.get("associations", {}).pop(key, None)
            if "refs" in article:
                article["refs"] = [r for r in article.get("refs", []) if r["key"] != key]

    def filter_blocks(self, item, field, filter, is_html=True):
        editor = Editor3Content(item, field, is_html)
        # assign special Ninjs FTP exporter
        exporter = NinjsFTPExporter(editor)
        exporter.set_formatter(self)
        editor.html_exporter = exporter
        blocks = []
        for block in editor.blocks:
            if filter(block):
                blocks.append(block)
        editor.set_blocks(blocks)
        editor.update_item()


class NinjsFTPExporter(DraftJSHTMLExporter):
    formatter = None

    def set_formatter(self, formatter):
        self.formatter = formatter

    def render_media(self, props):
        # we need to retrieve the key, there is not straightforward way to do it
        # so we find the key in entityMap with a corresponding value
        embed_key = next(
            k for k, v in self.content_state["entityMap"].items() if v["data"].get("media") == props["media"]
        )
        media_props = props["media"]
        media_type = media_props.get("type", "picture")

        rendition = media_props["renditions"].get("original") or media_props["renditions"]["viewImage"]
        alt_text = media_props.get("alt_text") or ""
        desc = media_props.get("description_text")
        if media_type == "picture":
            path = self.formatter.path

            renditions_to_publish = self.formatter.internal_renditions + list(
                get_renditions_spec(without_internal_renditions=True).keys()
            )

            renditions = media_props.get("renditions")
            # filter the renditions for those we wish to publish
            renditions = {name: rendition for name, rendition in renditions.items() if name in renditions_to_publish}

            if renditions:
                for name, rendition in renditions.items():
                    rendition["href"] = (
                        path.lstrip("/")
                        + ("/" if not path.endswith("/") and path else "")
                        + get_rendition_file_name(rendition)
                    )

            src = self.get_source_ref(renditions)
            srcset = self.get_source_set_refs(renditions)

            embed_type = "Image"
            elt = DOM.create_element(
                "img",
                {"src": src, "srcset": srcset, "sizes": "80vw", "alt": alt_text, "id": f"editor_{embed_key}"},
                props["children"],
            )
        elif media_type == "video":
            embed_type = "Video"
            src = (
                self.formatter.path.lstrip("/")
                + ("/" if not self.formatter.path.endswith("/") and self.formatter.path else "")
                + get_rendition_file_name(rendition)
            )
            # It seems impossible to add an attribute that has no value for "controls" the W3C validator accepts an
            # empty string
            elt = DOM.create_element(
                "video",
                {"controls": "", "src": src, "title": alt_text, "id": f"editor_{embed_key}"},
                props["children"],
            )
        elif media_type == "audio":
            embed_type = "Audio"
            src = (
                self.formatter.path.lstrip("/")
                + ("/" if not self.formatter.path.endswith("/") and self.formatter.path else "")
                + get_rendition_file_name(rendition)
            )
            elt = DOM.create_element(
                "audio",
                {"controls": "", "src": src, "title": alt_text, "id": f"editor_{embed_key}"},
                props["children"],
            )
        else:
            logger.error("Invalid or not implemented media type: {media_type}".format(media_type=media_type))
            return None

        content = DOM.render(elt)

        if desc:
            content += "<figcaption>{}</figcaption>".format(desc)

        # <dummy_tag> is needed for the comments, because a root node is necessary
        # it will be removed during rendering.
        embed = DOM.parse_html(
            dedent(
                """\
            <dummy_tag><!-- EMBED START {embed_type} {{id: "editor_{key}"}} -->
            <figure>{content}</figure>
            <!-- EMBED END {embed_type} {{id: "editor_{key}"}} --></dummy_tag>"""
            ).format(embed_type=embed_type, key=embed_key, content=content)
        )

        return embed

    def get_source_ref(self, renditions):
        try:
            return renditions.get("original").get("href")
        except Exception:
            widest = -1
            src_rendition = ""
            for rendition in renditions:
                width = renditions.get(rendition).get("width")
                if width > widest:
                    widest = width
                    src_rendition = rendition

        if widest > 0:
            return renditions.get(src_rendition).get("href").lstrip("/")

        logger.warning("href not found in FTP NINJS formatter, ensure the formatter has it enabled")
        return None

    def get_source_set_refs(self, renditions):
        try:
            srcset = []
            for rendition in renditions:
                srcset.append(
                    renditions.get(rendition).get("href").lstrip("/")
                    + " "
                    + str(renditions.get(rendition).get("width"))
                    + "w"
                )
            return ",".join(srcset)
        except Exception:
            return None
