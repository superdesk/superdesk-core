import superdesk

from typing import Any, Dict, List, Literal

from . import privileges, types, rundowns

from superdesk.metadata.item import metadata_schema


class RundownItemsResource(superdesk.Resource):
    resource_title = "rundown_items"

    schema = {
        "title": metadata_schema["headline"],
        "item_type": superdesk.Resource.not_analyzed_field(required=True),
        "content": metadata_schema["body_html"],
        "duration": {
            "type": "number",
        },
        "planned_duration": {
            "type": "number",
        },
        "show_part": superdesk.Resource.not_analyzed_field(),
        "live_sound": superdesk.Resource.not_analyzed_field(),
        "guests": superdesk.Resource.not_analyzed_field(),
        "additional_notes": superdesk.Resource.not_analyzed_field(),
        "live_captions": superdesk.Resource.not_analyzed_field(),
        "last_sentence": superdesk.Resource.not_analyzed_field(),
        "fields_meta": metadata_schema["fields_meta"].copy(),
        "subitems": {"type": "list", "mapping": {"type": "keyword"}},
        "subitem_attachments": {"type": "list", "mapping": {"type": "keyword"}},
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


class RundownItemsService(superdesk.Service):
    search_fields = [
        "title",
        "content",
        "live_captions",
        "additional_notes",
    ]

    duration_fields = [
        "duration",
        "planned_duration",
    ]

    def create_from_template(self, template: types.IRundownItemTemplate) -> types.IRundownItem:
        item: types.IRundownItem = {
            "item_type": template["item_type"],
            "title": template.get("title", ""),
            "duration": template.get("duration", 0),
            "planned_duration": template.get("planned_duration", 0),
            "content": template.get("content", ""),
            "show_part": template.get("show_part", ""),
            "live_sound": template.get("live_sound", ""),
            "guests": template.get("guests", ""),
            "additional_notes": template.get("additional_notes", ""),
            "live_captions": template.get("live_captions", ""),
            "last_sentence": template.get("last_sentence", ""),
        }

        self.create([item])
        return item

    def sync_items(self, dest: types.IRundown, refs: types.IRefs) -> None:
        """Sync items data to rundown."""
        durations: Dict[Literal["duration", "planned_duration"], Dict[str, int]] = {
            "duration": {},
            "planned_duration": {},
        }
        cursor = self.get_from_mongo(req=None, lookup={"_id": {"$in": [ref["_id"] for ref in refs]}})
        # first we store durations for each item in a lookup
        dest["items_data"] = []
        for item in cursor:
            for key in durations:
                durations[key][str(item["_id"])] = item.get(key) or 0
            for field in self.search_fields:
                if item.get(field):
                    dest["items_data"].append(
                        {
                            "_id": item["_id"],
                            "key": field,
                            "value": item[field],
                        }
                    )

        # for each duration we iterate over refs and compute durations
        for key in durations:
            dest[key] = 0
            for ref in refs:
                dest[key] += durations[key][str(ref["_id"])]

    def get_rundown_items(self, rundown: types.IRundown) -> List[types.IRundownItem]:
        if not rundown.get("items"):
            return []
        ids = list(set([ref["_id"] for ref in rundown["items"]]))
        items = {}
        cursor = self.get_from_mongo(req=None, lookup={"_id": {"$in": ids}})
        for item in cursor:
            items[item["_id"]] = item
        return [items[ref["_id"]] for ref in rundown["items"]]

    def on_updated(self, updates, original):
        for field in self.search_fields + self.duration_fields:
            if field in updates and original.get(field) != updates[field]:
                rundowns.rundowns_service.sync_item_changes(original["_id"])
                break


items_service = RundownItemsService()
