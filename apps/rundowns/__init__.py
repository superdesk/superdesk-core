import superdesk

from flask_babel import lazy_gettext

from superdesk.factory.app import SuperdeskEve

from . import shows, templates, privileges


def init_app(app: SuperdeskEve) -> None:
    superdesk.privilege(
        name=privileges.RUNDOWNS,
        label=lazy_gettext("Rundowns"),
        description=lazy_gettext("Rundowns module"),
    )

    superdesk.register_resource("rundown_shows", shows.ShowsResource, shows.ShowsService, _app=app)
    superdesk.register_resource("rundown_templates", templates.TemplatesResource, templates.TemplatesService, _app=app)

    app.item_scope(
        "rundowns",
        schema={
            "duration": {
                "type": "number",
            },
        },
    )
