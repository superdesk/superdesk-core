import superdesk

from typing import Final
from flask_babel import lazy_gettext

from superdesk.factory.app import SuperdeskApp

SCOPE: Final = "rundowns"

from . import (  # noqa: E402
    shows,
    templates,
    privileges,
    rundowns,
    rundown_items,
    tasks,
    export,
)


def init_app(app: SuperdeskApp) -> None:
    superdesk.privilege(
        name=privileges.RUNDOWNS,
        label=lazy_gettext("Rundowns"),
        description=lazy_gettext("Rundowns management"),
    )

    superdesk.register_resource("shows", shows.ShowsResource, service_instance=shows.shows_service, _app=app)
    superdesk.register_resource(
        "rundowns", rundowns.RundownsResource, service_instance=rundowns.rundowns_service, _app=app
    )
    superdesk.register_resource(
        "rundown_items", rundown_items.RundownItemsResource, service_instance=rundown_items.items_service, _app=app
    )
    superdesk.register_resource(
        "rundown_templates", templates.TemplatesResource, service_instance=templates.templates_service, _app=app
    )
    superdesk.register_resource(
        "rundown_export", export.ExportResource, service_instance=export.export_service, _app=app
    )

    from .formatters.pdf import PrompterPDFFormatter

    export.available_services.append(
        PrompterPDFFormatter("prompter-pdf", "Prompter"),
    )

    app.register_blueprint(export.blueprint)
