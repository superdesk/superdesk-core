import base64

from flask import render_template

from . import BaseFormatter

from superdesk.text_utils import get_text


def rundown_item_content(item) -> str:
    if item.get("content"):
        return "<br />".join(get_text(item["content"], "html", lf_on_block=True).strip().splitlines())
    return ""


class HtmlFormatter(BaseFormatter):
    def __init__(self, id, name, template):
        super().__init__(id, name)
        self.template = template

    def export(self, dest, show, rundown, items):
        html = render_template(self.template, show=show, rundown=rundown, items=items)
        dest["content"] = base64.b64encode(html.encode("utf-8"))
        dest["content_type"] = "text/html"
