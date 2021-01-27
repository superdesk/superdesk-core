from flask_babel import lazy_gettext
import superdesk


superdesk.privilege(
    name="feature_preview",
    label=lazy_gettext("Feature Preview"),
    description=lazy_gettext("Let user toggle Feature Preview on/off."),
)
