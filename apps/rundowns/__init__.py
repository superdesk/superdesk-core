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
        "rundown_from_template", create.FromTemplateResource, create.FromTemplateService, backend=None, _app=app
    )

    app.item_scope(
        SCOPE,
        schema={
            "duration": {
                "type": "number",
            },
        },
    )
