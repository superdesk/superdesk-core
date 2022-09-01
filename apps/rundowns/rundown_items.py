import superdesk

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
            "last_sentences": template.get("last_sentences", ""),
        }

        self.create([item])
        return item

    def get_durations(self, refs: types.IRefs) -> int:
        durations = {}
        cursor = self.get_from_mongo(
            req=None, lookup={"_id": {"$in": [ref["_id"] for ref in refs]}}, projection={"duration": 1}
        )
        for item in cursor:
            durations[item["_id"]] = item["duration"]
        duration = 0
        for ref in refs:
            duration += durations[ref["_id"]]
        return duration

    def on_updated(self, updates, original):
        if "duration" in updates and original.get("duration") != updates["duration"]:
            rundowns.rundowns_service.update_durations(original["_id"])


items_service = RundownItemsService()
