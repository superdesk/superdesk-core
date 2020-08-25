
import superdesk
from flask_babel import _


def init_app(app):
    superdesk.register_default_user_preference('monitoring:view', {
        'type': 'string',
        'allowed': ['list', 'swimlane'],
        'view': 'list',
        'default': 'list',
        'label': _('Monitoring view'),
        'category': _('monitoring'),
    })

    superdesk.register_default_session_preference('monitoring:view:session', None)
