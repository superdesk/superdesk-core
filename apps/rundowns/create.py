import datetime
import superdesk

from typing import Dict, List, Literal, Optional, TypedDict

from flask import current_app as app
from eve.methods.common import document_link
from apps.packages.package_service import get_item_ref

from . import privileges, SCOPE


class IEntity(TypedDict, total=False):
    _id: str
    _links: Dict


class IRef(TypedDict, total=False):
    _id: str
    idRef: str
    planned_duration: int
    start_time: str


class IGroup(TypedDict):
    role: str
    refs: List[IRef]


class IRundown(IEntity):
    scope: Literal["rundowns"]
    type: Literal["composite"]
    particular_type: str
    show: str
    airtime_date: str
    airtime_time: str
    headline: str
    planned_duration: int
    rundown_template: str
    rundown_scheduled_on: datetime.datetime
    groups: List[IGroup]


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


def create_rundown_from_template(
    template, date: datetime.date, scheduled_on: Optional[datetime.datetime] = None
) -> IRundown:
    rundown: IRundown = {
        "scope": SCOPE,
        "type": "composite",
        "particular_type": "rundown",
        "show": template["show"],
        "airtime_date": date.isoformat(),
        "airtime_time": template.get("airtime_time", ""),
        "headline": template.get("headline", ""),
        "planned_duration": template.get("planned_duration", 0),
        "rundown_template": template["_id"],
        "rundown_scheduled_on": scheduled_on or datetime.datetime.utcnow(),
        "groups": [],
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

    if template.get("groups"):
        for group in template["groups"]:
            rundown["groups"].append(
                {
                    "role": group["role"],
                    "refs": [duplicate_group_item(ref) for ref in group["refs"] if ref.get("residRef")],
                }
            )

    superdesk.get_resource_service("rundowns").post([rundown])
    return rundown


def duplicate_group_item(ref: IRef) -> IRef:
    items_service = superdesk.get_resource_service("rundown_items")
    assert "residRef" in ref
    item = items_service.find_one(req=None, _id=ref["residRef"])
    copy = items_service.copy_item(item)
    items_service.post([copy])
    new_ref: IRef = get_item_ref(copy)  # type: ignore
    for field in ("planned_duration", "start_time"):
        if ref.get(field):
            new_ref[field] = ref[field]
    return new_ref


class FromTemplateService(superdesk.Service):
    def create(self, docs, **kwargs):
        ids = []
        for doc in docs:
            template = superdesk.get_resource_service("rundown_templates").find_one(req=None, _id=doc["template"])
            assert template
            date = datetime.date.fromisoformat(doc["airtime_date"])
            rundown = create_rundown_from_template(template, date)
            assert "_id" in rundown
            rundown["_links"] = {"self": {
                "href": f'rundowns/{rundown["_id"]}',
                "title": "Rundowns",
            }}
            doc.update(rundown)
            ids.append(rundown["_id"])
            return ids
