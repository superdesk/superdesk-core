import superdesk

from flask_babel import lazy_gettext

from superdesk.factory.app import SuperdeskEve

SCOPE = "rundowns"

from . import shows, templates, privileges, create  # noqa: E402


def init_app(app: SuperdeskEve) -> None:
    superdesk.privilege(
        name=privileges.RUNDOWNS,
        label=lazy_gettext("Rundowns"),
        description=lazy_gettext("Rundowns management"),
    )

    superdesk.register_resource("shows", shows.ShowsResource, shows.ShowsService, _app=app)
    superdesk.register_resource("rundown_templates", templates.TemplatesResource, templates.TemplatesService, _app=app)
    superdesk.register_resource(
        "show_rundowns", create.FromTemplateResource, create.FromTemplateService, backend=None, _app=app
    )

    app.item_scope(
        SCOPE,
        schema={
            "show": superdesk.Resource.rel("shows"),
            "rundown_template": superdesk.Resource.rel("rundown_templates"),
            "planned_duration": {
                "type": "number",
            },
            "airtime_time": {
                "type": "string",
            },
            "airtime_date": {
                "type": "string",
            },
        },
    )
