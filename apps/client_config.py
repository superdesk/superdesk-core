import superdesk

from flask import current_app as app
from superdesk.utils import ListCursor


class ClientConfigResource(superdesk.Resource):
    item_methods = []
    public_methods = ["GET"]
    resource_methods = ["GET"]


class ClientConfigService(superdesk.Service):
    def get(self, req, lookup):
        return ListCursor()

    def on_fetched(self, docs):
        docs["config"] = getattr(app, "client_config", {})


def init_app(app) -> None:
    superdesk.register_resource("client_config", ClientConfigResource, ClientConfigService, _app=app)
    app.client_config.update(
        {
            "schema": app.config.get("SCHEMA"),
            "editor": app.config.get("EDITOR"),
            "feedback_url": app.config.get("FEEDBACK_URL"),
            "override_ednote_for_corrections": app.config.get("OVERRIDE_EDNOTE_FOR_CORRECTIONS", True),
            "override_ednote_template": app.config.get("OVERRIDE_EDNOTE_TEMPLATE"),
            "default_genre": app.config.get("DEFAULT_GENRE_VALUE_FOR_MANUAL_ARTICLES"),
            "japanese_characters_per_minute": app.config.get("JAPANESE_CHARACTERS_PER_MINUTE"),
            "validator_media_metadata": app.config.get("VALIDATOR_MEDIA_METADATA", {}),
            "publish_content_expiry_minutes": app.config.get("PUBLISHED_CONTENT_EXPIRY_MINUTES", 0),
            "high_priority_queue_enabled": app.config.get("HIGH_PRIORITY_QUEUE_ENABLED"),
            "default_language": app.config.get("DEFAULT_LANGUAGE"),
            "workflow_allow_multiple_updates": app.config.get("WORKFLOW_ALLOW_MULTIPLE_UPDATES"),
            "workflow_allow_duplicate_non_members": app.config.get("WORKFLOW_ALLOW_DUPLICATE_NON_MEMBERS"),
            "disallowed_characters": app.config.get("DISALLOWED_CHARACTERS"),
            "allow_updating_scheduled_items": app.config.get("ALLOW_UPDATING_SCHEDULED_ITEMS"),
            "corrections_workflow": app.config.get("CORRECTIONS_WORKFLOW"),
        }
    )
