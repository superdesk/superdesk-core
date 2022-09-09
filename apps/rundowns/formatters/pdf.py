import io
import reportlab.lib.colors as colors

from typing import List

from reportlab.platypus import SimpleDocTemplate, Paragraph, ListItem, ListFlowable, Table
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import landscape, A4

from superdesk.editor_utils import get_field_content_state

from . import BaseFormatter, utils
from .csv import TableCSVFormatter

from superdesk.text_utils import get_text


styles = getSampleStyleSheet()


FONT_SIZE = 14
FONT_NAME = styles["Heading1"].fontName
ORDERED_TYPE = "1"
UNORDERED_TYPE = "bullet"


styles["OrderedList"].bulletFormat = "%s."
styles["OrderedList"].bulletFontSize = FONT_SIZE
styles["OrderedList"].bulletFontName = FONT_NAME
styles["OrderedList"].leftIndent = FONT_SIZE * 2
styles["UnorderedList"].bulletFontSize = FONT_SIZE
styles["UnorderedList"].bulletFontName = FONT_NAME
styles["UnorderedList"].leftIndent = FONT_SIZE * 2
styles["BodyText"].fontName = FONT_NAME
styles["BodyText"].fontSize = FONT_SIZE
styles["BodyText"].leading = FONT_SIZE + 5
styles["BodyText"].spaceAfter = FONT_SIZE


class PrompterPDFFormatter(BaseFormatter):

    MIMETYPE = "application/pdf"

    style = styles["BodyText"]
    margin = FONT_SIZE

    pagesize = A4

    def filename(self, show, rundown):
        return f"Prompter-{rundown['title']}.pdf"

    def export(self, show, rundown, items):
        output = io.BytesIO()
        doc = SimpleDocTemplate(
            output,
            leftMargin=self.margin,
            rightMargin=self.margin,
            topMargin=self.margin,
            bottomMargin=self.margin,
            title=rundown["title"],
            pagesize=self.pagesize,
        )

        contents = self.get_contents(show, rundown, items)
        doc.build(contents)

        return output.getvalue(), self.MIMETYPE, self.filename(show, rundown)

    def get_contents(self, show, rundown, items):
        contents = []
        for item in items:
            self.export_item(contents, show, rundown, item)
        return contents

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


class TablePDFFormatter(PrompterPDFFormatter):

    MIMETYPE = "application/pdf"

    pagesize = landscape(A4)

    def filename(self, show, rundown):
        return f"Realizer-{rundown['title']}.pdf"

    def get_contents(self, show, rundown, items):
        data = [
            TableCSVFormatter.COLUMNS,
        ]
        for i, item in enumerate(items, start=1):
            data.append(utils.item_table_data(show, rundown, item, i))
        return [
            Table(
                data,
                style=[
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.black),
                ],
            )
        ]
