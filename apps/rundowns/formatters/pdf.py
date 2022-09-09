import io
from typing import List

from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

from superdesk.editor_utils import get_field_content_state

from . import BaseFormatter

from superdesk.text_utils import get_text


styles = getSampleStyleSheet()


class PrompterPDFFormatter(BaseFormatter):

    MIMETYPE = "application/pdf"

    style = styles["BodyText"]
    style.fontSize = 15
    style.spaceAfter = 15

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
        for block in content_state["blocks"]:
            if block["type"] == "unstyled" and block.get("text"):
                contents.append(Paragraph(block["text"], self.style))
            elif block["type"] == "unordered-list-item" and block.get("text"):
                contents.append(Paragraph(block["text"], self.style, bulletText=self.bullet))
