import io
from typing import List

from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

from . import BaseFormatter

from superdesk.text_utils import get_text


styles = getSampleStyleSheet()


class PrompterPDFFormatter(BaseFormatter):

    MIMETYPE = "application/pdf"

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

    def export_item(self, contents: List, show, rundown, item):
        title = "-".join(
            [
                item["item_type"].upper(),
                show["shortcode"].upper(),
                item["title"].upper(),
            ]
        )
        contents.append(Paragraph(title, styles["Heading2"]))
        if item.get("content"):
            text = get_text(item["content"], "html", lf_on_block=True).strip()
            contents.append(Paragraph(text, styles["BodyText"]))

        contents.append(Paragraph("", styles["BodyText"]))
