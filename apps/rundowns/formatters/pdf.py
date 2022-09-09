import io
from typing import List

from reportlab.platypus import SimpleDocTemplate, Paragraph, ListItem, ListFlowable
from reportlab.lib.styles import getSampleStyleSheet

from superdesk.editor_utils import get_field_content_state

from . import BaseFormatter

from superdesk.text_utils import get_text


FONT_SIZE = 15
ORDERED_TYPE = "1"
UNORDERED_TYPE = "bullet"


styles = getSampleStyleSheet()
styles["OrderedList"].bulletFontSize = FONT_SIZE
styles["OrderedList"].bulletFormat = "%s."
styles["UnorderedList"].bulletFontSize = FONT_SIZE


class PrompterPDFFormatter(BaseFormatter):

    MIMETYPE = "application/pdf"

    style = styles["BodyText"]
    style.fontSize = FONT_SIZE
    style.spaceAfter = FONT_SIZE

    bullet = "\u2022"  # unicode bullet

    def export(self, show, rundown, items):
        filename = f"{rundown['title']}.pdf"
        output = io.BytesIO()

        margin = 15
        doc = SimpleDocTemplate(
            output, leftMargin=margin, rightMargin=margin, topMargin=margin, bottomMargin=margin, title=rundown["title"]
        )
        contents = []
        for item in items:
            self.export_item(contents, show, rundown, item)
        doc.build(contents)

        return output.getvalue(), self.MIMETYPE, filename

    def export_item(self, contents: List, show, rundown, item) -> None:
        title = "-".join(
            filter(
                None,
                [
                    item.get("item_type", "").upper(),
                    show.get("shortcode", "").upper(),
                    item.get("title", "").upper(),
                ],
            )
        )
        contents.append(Paragraph(title, self.style))

        content_state = get_field_content_state(item, "content")
        if content_state:
            self.export_item_content_state(contents, content_state)
        elif item.get("content"):
            text = get_text(item["content"], "html", lf_on_block=True).strip()
            contents.append(Paragraph(text, self.style))

        # empty line after item
        contents.append(Paragraph("", self.style))

    def export_item_content_state(self, contents: List, content_state) -> None:
        list_type = None
        list_items = []
        for block in content_state["blocks"]:
            if block["type"] == "unstyled":
                if list_items:
                    contents.append(self.list(list_items, list_type))
                    list_type = None
                    list_items = []
                contents.append(Paragraph(block["text"], self.style))
            elif block["type"] == "unordered-list-item":
                if list_type and list_type != UNORDERED_TYPE:
                    contents.append(self.list(list_items, list_type))
                    list_items = []
                list_type = UNORDERED_TYPE
                list_items.append(
                    ListItem(Paragraph(block["text"], self.style), bulletType="bullet", style=styles["UnorderedList"])
                )
            elif block["type"] == "ordered-list-item":
                if list_type and list_type != ORDERED_TYPE:
                    contents.append(self.list(list_items, list_type))
                    list_items = []
                list_type = ORDERED_TYPE
                list_items.append(
                    ListItem(Paragraph(block["text"], self.style), bulletType="1", style=styles["OrderedList"])
                )
        if list_items:
            contents.append(self.list(list_items, list_type))

    def list(self, items, type):
        return ListFlowable(items, bulletType=type)
