import superdesk

from . import privileges


class TemplatesResource(superdesk.Resource):
    url = r'/shows/<regex("[a-f0-9]{24}"):show>/templates'
    resource_title = "rundown_templates"
    schema = {
        "name": {
            "type": "string",
            "required": True,
        },
        "show": superdesk.Resource.rel("shows", required=True),
        "description": {
            "type": "string",
        },
        "airtime_time": {
            "type": "string",
            "regex": r"[0-9]{2}:[0-9]{2}(:[0-9]{2})?$",
        },
        "planned_duration": {
            "type": "number",
        },
        "schedule": {
            "type": "dict",
            "schema": {
                "is_active": {
                    "type": "boolean",
                },
                "day_of_week": {
                    "type": "list",
                    "allowed": ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"],
                },
            },
        },
        "headline": {
            "type": "string",
        },
        "created_by": superdesk.Resource.rel("users"),
        "updated_by": superdesk.Resource.rel("users"),
    }

    privileges = {"POST": privileges.RUNDOWNS, "PATCH": privileges.RUNDOWNS, "DELETE": privileges.RUNDOWNS}


def fix_self_link(doc) -> None:
    if "_links" not in doc:
        return
    doc["_links"]["self"]["href"] = "/shows/{show}/templates/{_id}".format(
        show=doc["show"],
        _id=doc["_id"],
    )


class TemplatesService(superdesk.Service):
    def on_created(self, docs):
        super().on_created(docs)
        for doc in docs:
            fix_self_link(doc)

    def on_fetched(self, response):
        super().on_fetched(response)
        for doc in response["_items"]:
            fix_self_link(doc)

    def on_fetched_item(self, doc):
        super().on_fetched_item(doc)
        fix_self_link(doc)
