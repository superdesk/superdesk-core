import pytz
import superdesk

from . import privileges, SCOPE

from flask import current_app as app
from eve.methods.common import document_link


class FromTemplateResource(superdesk.Resource):
    url = r'/rundown_shows/<regex("[a-f0-9]{24}"):show>/rundowns'
    schema = {
        "template": superdesk.Resource.rel("rundown_templates", required=True),
        "date": {
            "type": "datetime",
        },
    }

    datasource = {
        "projection": {
            "_links": 1,
            "headline": 1,
            "planned_duration": 1,
        },
    }

    item_methods = []
    resource_methods = ["POST"]
    privileges = {"POST": privileges.RUNDOWNS}


class FromTemplateService(superdesk.Service):
    def create(self, docs, **kwargs):
        ids = []
        for doc in docs:
            template = superdesk.get_resource_service("rundown_templates").find_one(req=None, _id=doc["template"])
            assert template
            rundown = {"scope": SCOPE, "type": "composite", "particular_type": "rundown"}

            date = doc["date"]

            if template.get("headline_template") and template.get("air_time"):
                air_time = template.get("air_time").split(":")
                date = date.replace(
                    hour=int(air_time[0]),
                    minute=int(air_time[1]),
                    second=int(air_time[2]) if len(air_time) == 3 else 0,
                    tzinfo=pytz.timezone(app.config["RUNDOWNS_TIMEZONE"]),
                    microsecond=0,
                )
                rundown["headline"] = " ".join(
                    filter(
                        bool,
                        [
                            template["headline_template"].get("prefix"),
                            template["headline_template"].get("separator", ""),
                            date.strftime(template["headline_template"].get("date_format", "")),
                        ],
                    )
                )

            if template.get("planned_duration"):
                rundown["planned_duration"] = template["planned_duration"]

            superdesk.get_resource_service("archive").post([rundown])
            rundown["_links"] = {"self": document_link("archive", rundown["_id"])}
            doc.update(rundown)
            ids.append(rundown.get("_id"))

        return ids
