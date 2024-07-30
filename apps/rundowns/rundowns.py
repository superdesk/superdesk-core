import bson
import datetime
import superdesk

from typing import Optional

from superdesk.core import json
from superdesk.metadata.item import metadata_schema
from werkzeug.datastructures import ImmutableMultiDict

from . import privileges, rundown_items, types, templates, shows


def get_date_format(_format: Optional[str] = None) -> str:
    """Convert client format to python format."""
    if not _format:
        _format = "DD.MM.YYYY"
    return _format.replace("DD", "%d").replace("MM", "%m").replace("YYYY", "%Y")


class RundownsResource(superdesk.Resource):
    resource_title = "rundowns"

    schema = {
        "show": superdesk.Resource.rel("shows", required=True),
        "title": metadata_schema["headline"],
        "template": superdesk.Resource.rel("rundown_templates", nullable=True),
        "scheduled_on": {
            "type": "datetime",
            "readonly": True,
            "nullable": True,
        },
        "duration": {
            "type": "number",
            "readonly": True,
        },
        "planned_duration": {
            "type": "number",
        },
        "airtime_time": {
            "type": "string",
            "mapping": {"type": "keyword"},
        },
        "airtime_date": {
            "type": "string",
            "mapping": {"type": "keyword"},
        },
        "items": {
            "type": "list",
            "schema": {
                "type": "dict",
                "schema": {
                    "_id": superdesk.Resource.rel("rundown_items", required=True),
                    "start_time": {"type": "time"},
                },
            },
        },
        "items_data": {
            "type": "list",
            "schema": {
                "type": "dict",
                "schema": {
                    "_id": superdesk.Resource.rel("rundown_items"),
                    "key": superdesk.Resource.not_analyzed_field(),
                    "value": superdesk.Resource.field("string", analyzed=True),
                },
            },
            "mapping": {
                "type": "nested",
                "properties": {
                    "_id": {"type": "keyword"},
                    "key": {"type": "keyword"},
                    "value": metadata_schema["body_html"]["mapping"],
                },
            },
        },
        "matching_items": {
            "type": "list",
            "readonly": True,
        },
    }

    datasource = {
        "search_backend": "elastic",
    }

    locking = True
    versioning = True
    privileges = {
        "POST": privileges.RUNDOWNS,
        "PATCH": privileges.RUNDOWNS,
        "PUT": privileges.RUNDOWNS,
        "DELETE": privileges.RUNDOWNS,
    }


class RundownsService(superdesk.Service):
    def create(self, docs, **kwargs):
        ids = []
        for doc in docs:
            show = shows.shows_service.find_one(req=None, _id=doc["show"])
            assert show is not None, {"show": 1}
            date = (
                datetime.date.fromisoformat(doc["airtime_date"]) if doc.get("airtime_date") else datetime.date.today()
            )
            if doc.get("template"):
                template = templates.templates_service.find_one(req=None, _id=doc["template"])
                assert template is not None, {"template": 1}
                rundown = self.create_from_template(template, date, doc=doc)
            else:
                rundown = self.create_from_show(show, date, doc=doc)
            doc.update(rundown)
            assert "_id" in rundown, {"rundown": {"_id": 1}}
            ids.append(rundown["_id"])
        return ids

    def create_from_show(self, show: types.IShow, date: datetime.date, *, doc: types.IRundown) -> types.IRundown:
        assert "_id" in show, {"show": {"_id": 1}}
        rundown: types.IRundown = {
            "show": show["_id"],
            "title": doc.get("title") or show["title"],
            "planned_duration": doc.get("planned_duration") or show.get("planned_duration") or 0,
            "airtime_date": date.isoformat(),
            "airtime_time": doc["airtime_time"] if "airtime_time" in doc else "",
            "scheduled_on": None,
            "items": doc["items"] if doc.get("items") else [],
            "items_data": [],
        }

        if rundown.get("items"):
            rundown_items.items_service.sync_items(rundown, rundown["items"])

        super().create([rundown])
        return rundown

    def create_from_template(
        self,
        template: types.IRundownTemplate,
        date: datetime.datetime,
        *,
        doc: Optional[types.IRundown] = None,
        scheduled_on: Optional[datetime.datetime] = None,
    ) -> types.IRundown:
        assert "_id" in template, {"template": {"_id": 1}}
        if doc is None:
            doc = {
                "show": "",
                "airtime_time": "",
                "airtime_date": date.isoformat(),
                "title": "",
                "duration": 0,
                "planned_duration": 0,
                "scheduled_on": None,
                "template": template["_id"],
                "items": [],
                "items_data": [],
            }
        rundown: types.IRundown = {
            "show": doc.get("show") or template.get("show") or "",
            "airtime_date": date.isoformat(),
            "airtime_time": doc.get("airtime_time") or template.get("airtime_time") or "",
            "title": doc.get("title") or template.get("title", "") or "",
            "template": template["_id"],
            "duration": 0,
            "planned_duration": doc.get("planned_duration") or template.get("planned_duration") or 0,
            "scheduled_on": scheduled_on,
            "items": [],
            "items_data": [],
        }

        if template.get("title_template") and not doc.get("title"):
            title_template = template["title_template"]
            rundown["title"] = " ".join(
                filter(
                    bool,
                    [
                        title_template.get("prefix") or "",
                        title_template.get("separator", " ").strip(),
                        date.strftime(get_date_format(title_template.get("date_format"))),
                    ],
                )
            )

        super().create([rundown])
        assert "_id" in rundown

        if template.get("items"):
            updates: types.IRundown = {}
            updates["items"] = [self.create_template_item(ref, rundown) for ref in template["items"]]
            rundown_items.items_service.sync_items(updates, updates["items"])
            super().system_update(bson.ObjectId(rundown["_id"]), updates, rundown)
            rundown.update(updates)

        return rundown

    def create_template_item(self, item_template: types.IRundownItemTemplate, rundown: types.IRundown) -> types.IRef:
        item = rundown_items.items_service.create_from_template(item_template, rundown)
        assert "_id" in item, {"rundown_item": {"_id": 1}}
        return {"_id": bson.ObjectId(item["_id"])}

    def update(self, id, updates, original):
        if updates.get("items"):
            if updates["items"] != original.get("items"):
                rundown_items.items_service.sync_items(updates, updates["items"])
        return super().update(id, updates, original)

    def sync_item_changes(self, item_id) -> None:
        cursor = self.get_from_mongo(req=None, lookup={"items._id": item_id})
        for rundown in cursor:
            updates: types.IRundown = {}
            rundown_items.items_service.sync_items(updates, rundown["items"])
            if updates:
                self.system_update(rundown["_id"], updates, rundown)

    def get(self, req, lookup):
        if req:
            source = json.loads(req.args.get("source")) if req.args.get("source") else {}
            query_string_query = None
            if source.get("query"):
                try:
                    query_string_query = source["query"]["filtered"]["query"]["query_string"]
                    query_string_query = {"query_string": query_string_query}
                    source["query"].pop("filtered")
                except KeyError:
                    query_string_query = None

            if req.args.get("q"):
                query_string_query = {
                    "query_string": {
                        "query": req.args.get("q"),
                        "default_operator": "AND",
                        "lenient": True,
                    },
                }

            if query_string_query:
                items_query = {
                    "nested": {
                        "path": "items_data",
                        "query": query_string_query,
                        "inner_hits": {"name": "rundown_items"},
                    },
                }

                query = {
                    "bool": {
                        "should": [
                            query_string_query,
                            items_query,
                        ],
                        "minimum_should_match": 1,
                    }
                }

                if source.get("query"):
                    old_query = source["query"]
                    source["query"] = query
                    query["bool"]["must"] = old_query
                else:
                    source["query"] = query

            args = req.args.to_dict()
            if args.get("q"):
                args.pop("q")
            args["source"] = json.dumps(source)
            req.args = ImmutableMultiDict(args)
            cursor = super().get(req, lookup)
            matching_items = set()
            for item in cursor.hits["hits"]["hits"]:
                if item.get("inner_hits"):
                    ids = [hit["_source"]["_id"] for hit in item["inner_hits"]["rundown_items"]["hits"]["hits"]]
                    for id in ids:
                        matching_items.add(id)
            if matching_items:
                items = list(
                    rundown_items.items_service.get_from_mongo(req=None, lookup={"_id": {"$in": list(matching_items)}})
                )
                for rundown in cursor:
                    rundown["matching_items"] = []
                    if not rundown.get("items"):
                        continue
                    for ref in rundown["items"]:
                        for item in items:
                            if str(item["_id"]) == str(ref["_id"]):
                                rundown["matching_items"].append(item)
            return cursor
        return super().get(req, lookup)


rundowns_service = RundownsService()
