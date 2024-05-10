import io
import reportlab.lib.colors as colors

from typing import List, Sequence, Union

from reportlab.platypus import SimpleDocTemplate, Paragraph, Flowable, Table
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.units import cm, inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from superdesk.editor_utils import get_field_content_state

from . import BaseFormatter, utils
from .. import utils as rundown_utils
from .csv import TableCSVFormatter

from superdesk.text_utils import get_text


styles = getSampleStyleSheet()

FONT_NAME = "DejaVuSans"
MONO_FONT_NAME = "DejaVuSansMono"
pdfmetrics.registerFont(TTFont(FONT_NAME, "DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont(MONO_FONT_NAME, "DejaVuSansMono.ttf"))

FONT_SIZE = 14
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
            title=rundown.get("title", ""),
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
        title = rundown_utils.item_title(show, rundown, item)
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
        for block in content_state["blocks"]:
            if block.get("text"):
                contents.append(Paragraph(block["text"], self.style))


class TablePDFFormatter(PrompterPDFFormatter):
    MIMETYPE = "application/pdf"

    pagesize = landscape(A4)

    def filename(self, show, rundown):
        return f"Technical-{rundown['title']}.pdf"

    def get_contents(self, show, rundown, items) -> List[Flowable]:
        subitems = utils.get_active_subitems(items)
        columns = utils.table_columns(subitems)
        data = [columns]
        for i, item in enumerate(items, start=1):
            item_cols = utils.item_table_data(show, rundown, item, i, subitems)
            for i in range(1, len(item_cols) - 1):
                # use paragraph for all columns but first and last, it allows for line breaks
                item_cols[i] = Paragraph(item_cols[i])
            data.append(item_cols)
        t = Table(
            data,
            colWidths=[inch, 1.5 * inch, 2.5 * inch, 2.5 * inch, 2.5 * inch, inch],
            style=[
                ("GRID", (0, 0), (-1, -1), 0.25, colors.black),
                ("FONTNAME", (0, 0), (-1, -1), MONO_FONT_NAME),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ],
        )
        t.hAlign = "LEFT"
        return [t]
