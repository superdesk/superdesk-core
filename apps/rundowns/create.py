import datetime
import superdesk

from typing import Dict, Literal, TypedDict
from eve.methods.common import document_link

from . import privileges, SCOPE


class IEntity(TypedDict, total=False):
    _id: str
    _links: Dict


class IRundown(IEntity):
    scope: Literal["rundowns"]
    type: Literal["composite"]
    particular_type: str
    show: str
    rundown_template: str
    airtime_date: str
    airtime_time: str
    headline: str
    planned_duration: int


class FromTemplateResource(superdesk.Resource):
    url = r'/shows/<regex("[a-f0-9]{24}"):show>/rundowns'
    schema = {
        "template": superdesk.Resource.rel("rundown_templates", required=True),
        "airtime_date": {
            "type": "string",
            "required": True,
        },
    }

    datasource = {
        "projection": {
            "_links": 1,
            "show": 1,
            "rundown_template": 1,
            "headline": 1,
            "planned_duration": 1,
            "airtime_time": 1,
            "airtime_date": 1,
        },
    }

    item_methods = []
    resource_methods = ["POST"]
    privileges = {"POST": privileges.RUNDOWNS}


def create_rundown_for_template(template, date: datetime.date) -> IRundown:
    rundown: IRundown = {
        "scope": SCOPE,
        "type": "composite",
        "particular_type": "rundown",
        "show": template["show"],
        "rundown_template": template["_id"],
        "airtime_date": date.isoformat(),
        "airtime_time": template.get("airtime_time", ""),
        "headline": template.get("headline", ""),
        "planned_duration": template.get("planned_duration", 0),
    }

    if template.get("headline_template"):
        headline_template = template["headline_template"]
        rundown["headline"] = " ".join(
            filter(
                bool,
                [
                    headline_template.get("prefix"),
                    headline_template.get("separator", " ").strip(),
                    date.strftime(headline_template.get("date_format", "%d.%m.%Y")),
                ],
            )
        )

    superdesk.get_resource_service("archive").post([rundown])
    return rundown


class FromTemplateService(superdesk.Service):
    def create(self, docs, **kwargs):
        ids = []
        for doc in docs:
            template = superdesk.get_resource_service("rundown_templates").find_one(req=None, _id=doc["template"])
            assert template
            date = datetime.date.fromisoformat(doc["airtime_date"])
            rundown = create_rundown_for_template(template, date)
            assert "_id" in rundown
            rundown["_links"] = {"self": document_link("archive", rundown["_id"])}
            doc.update(rundown)
            ids.append(rundown["_id"])

            return ids
