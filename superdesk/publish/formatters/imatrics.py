from superdesk.text_utils import get_text
from .ninjs_formatter import NINJSFormatter


def format_datetime(date):
    return date.isoformat()


class IMatricsFormatter(NINJSFormatter):
    def can_format(self, format_type, article):
        return format_type.lower() == "imatrics" and article.get("type") == "text"

    def _transform_to_ninjs(self, article, subscriber, recursive=True):
        return {
            "uuid": article["guid"],
            "createdTimestamp": format_datetime(article["firstcreated"]),
            "latestVersionTimestamp": format_datetime(article["versioncreated"]),
            "publicationTimestamp": format_datetime(article["firstpublished"]),
            "authors": [author["sub_label"] for author in article.get("authors") or []],
            "language": article["language"],
            "pubStatus": True,
            "concepts": self._format_concepts(article),
            "headline": get_text(article["headline"]),
            "preamble": get_text(article["abstract"], lf_on_block=True).strip() if article.get("abstract") else "",
            "dateline": article["dateline"]["text"]
            if article.get("dateline") and article["dateline"].get("text")
            else "",
            "body": [line.strip() for line in get_text(article["body_html"], lf_on_block=True).split("\n") if line],
        }

    def _format_concepts(self, article):
        concepts = []
        if article.get("subject"):
            concepts.extend(
                [
                    {
                        "type": "topic" if subj.get("scheme") == "imatrics_topic" else "category",
                        "title": subj["name"],
                        "uuid": subj["altids"]["imatrics"],
                    }
                    for subj in article["subject"]
                    if subj.get("altids") and subj["altids"].get("imatrics")
                ]
            )
        for _type in ("organisation", "person", "place", "event", "object"):
            if not article.get(_type):
                continue
            concepts.extend(
                [
                    {
                        "type": _type,
                        "title": concept["name"],
                        "uuid": concept["altids"]["imatrics"],
                    }
                    for concept in article[_type]
                    if concept.get("altids") and concept["altids"].get("imatrics")
                ]
            )
        return concepts
