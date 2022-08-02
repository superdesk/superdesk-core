import superdesk

from typing import Dict

from . import privileges

from superdesk.metadata.item import metadata_schema


class RundownItemsResource(superdesk.Resource):
    schema = {
        "headline": metadata_schema["headline"],
        "item_type": superdesk.Resource.not_analyzed_field(),
        "content": {
            "type": "string",
            "mapping": {"type": "string", "analyzer": "html_field_analyzer", "search_analyzer": "html_field_analyzer"},
        },
        "duration": {
            "type": "number",
        },
        "planned_duration": {
            "type": "number",
        },
    }

    datasource = {
        "search_backend": "elastic",
    }

    versioning = True
    privileges = {"POST": privileges.RUNDOWNS, "PATCH": privileges.RUNDOWNS, "PUT": privileges.RUNDOWNS}


class RundownItemsService(superdesk.Service):
    def copy_item(self, item: Dict):
        copy = {
            k: v
            for k, v in item.items()
            if k in RundownItemsResource.schema
        }

        return copy

