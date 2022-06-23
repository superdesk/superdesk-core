import pytz
import datetime
import superdesk


from flask import current_app as app
from flask_babel import _
from superdesk.errors import DocumentError
from superdesk.utc import local_to_utc

from . import privileges, utils


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
            "type": "time",
        },
        "airtime_date": {
            "type": "date",
        },
        "planned_duration": {
            "type": "number",
        },
        "repeat": {
            "type": "boolean",
        },
        "schedule": {
            "type": "dict",
            "schema": {
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
                    "allowed": list(range(-31, 32)),
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
        "scheduled_on": {
            "type": "datetime",
            "readonly": True,
        },
        "last_scheduled_on": {
            "type": "datetime",
            "readonly": True,
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
    def set_scheduled_on(self, updates, original=None):
        if original is None:
            original = {}

        def is_updated(field):
            return updates.get(field) and updates[field] != original.get(field)

        def is_none(field):
            return field in updates and updates[field] is None

        date_time_updated = is_updated("airtime_date") or is_updated("airtime_time")
        if not date_time_updated:
            return

        if is_none("airtime_date") or is_none("airtime_time"):
            updates["scheduled_on"] = None
            return

        airtime_date = updates.get("airtime_date") or original.get("airtime_date")
        airtime_time = updates.get("airtime_time") or original.get("airtime_time")
        if not airtime_date or not airtime_time:
            updates["scheduled_on"] = None
            return

        tz = pytz.timezone(app.config["RUNDOWNS_TIMEZONE"])
        now = datetime.datetime.now(tz=tz)
        date = utils.parse_date(airtime_date)
        time = utils.parse_time(airtime_time)
        scheduled_on = utils.combine_date_time(date, time, tz)

        if scheduled_on < now:
            raise DocumentError(_("Airtime must be in the future."))

        if scheduled_on >= now:
            updates["scheduled_on"] = local_to_utc(str(tz), scheduled_on)
            return

    def on_create(self, docs):
        for doc in docs:
            self.set_scheduled_on(doc)

    def on_update(self, updates, original):
        self.set_scheduled_on(updates, original)

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
