import datetime
import superdesk

from typing import Dict, List, Optional, TypedDict

from . import privileges, rundown_items, rundowns, templates


class IEntity(TypedDict, total=False):
    _id: str
    _links: Dict


class IRef(TypedDict):
    _id: str
    start_time: str


class IRundownTitleTemplate(TypedDict, total=False):
    prefix: str
    separator: str
    date_format: str


class IRundownBase(IEntity):
    title: str
    show: str
    airtime_date: str
    airtime_time: str
    planned_duration: int
    scheduled_on: datetime.datetime
    items: List[IRef]


class ITemplate(IRundownBase):
    title_template: IRundownTitleTemplate


class IRundown(IRundownBase):
    template: str


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
            "title": 1,
            "template": 1,
            "planned_duration": 1,
            "airtime_time": 1,
            "airtime_date": 1,
            "items": 1,
        },
    }

    item_methods = []
    resource_methods = ["POST"]
    privileges = {"POST": privileges.RUNDOWNS}


def create_rundown_from_template(
    template: ITemplate, date: datetime.date, scheduled_on: Optional[datetime.datetime] = None
) -> IRundown:
    rundown: IRundown = {
        "show": template["show"],
        "airtime_date": date.isoformat(),
        "airtime_time": template.get("airtime_time", ""),
        "title": template.get("title", ""),
        "template": template["_id"],
        "planned_duration": template.get("planned_duration", 0),
        "scheduled_on": scheduled_on or datetime.datetime.utcnow(),
        "items": [],
    }

    if template.get("title_template"):
        title_template = template["title_template"]
        rundown["title"] = " ".join(
            filter(
                bool,
                [
                    title_template.get("prefix") or "",
                    title_template.get("separator", " ").strip(),
                    date.strftime(title_template.get("date_format", "%d.%m.%Y")),
                ],
            )
        )

    if template.get("items"):
        rundown["items"] = [
            duplicate_item(ref) for ref in template["items"]
        ]

    rundowns.rundowns_service.post([rundown])
    return rundown


def duplicate_item(ref: IRef) -> IRef:
    items_service = rundown_items.items_service
    item = items_service.find_one(req=None, _id=ref["_id"])
    copy = items_service.copy_item(item)
    print("POST", copy)
    items_service.post([copy])
    new_ref: IRef = {
        "_id": copy["_id"],
        "start_time": ref["start_time"],
    }
    print("ref", ref, new_ref)
    return new_ref


class FromTemplateService(superdesk.Service):
    def create(self, docs, **kwargs):
        ids = []
        for doc in docs:
            template = templates.templates_service.find_one(req=None, _id=doc["template"])
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
