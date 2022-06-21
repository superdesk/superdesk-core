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
                "freq": {
                    "type": "string",
                    "allowed": ["DAILY", "WEEKLY", "MONTHLY", "YEARLY"],
                },
                "interval": {
                    "type": "number",
                    "default": 1,
                },
                "month": {
                    "type": "list",
                    "allowed": list(range(1, 13)),
                },
                "monthday": {
                    "type": "list",
                    "allowed": list(range(1, 32)),
                },
                "weekday": {
                    "type": "list",
                    "allowed": list(range(0, 7)),
                },
            },
        },
        "headline_template": {
            "type": "dict",
            "schema": {
                "prefix": {
                    "type": "string",
                },
                "separator": {
                    "type": "string",
                },
                "date_format": {
                    "type": "string",
                },
            },
        },
        "headline": {
            "type": "string",
        },
        "last_scheduled": {
            "type": "datetime",
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
