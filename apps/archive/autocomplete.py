
import locale
import warnings
import superdesk

from flask import current_app as app, request
from flask_babel import _
from datetime import timedelta
from superdesk.utils import ListCursor
from superdesk.utc import utcnow
from superdesk.errors import SuperdeskApiError


SETTING_ENABLED = 'ARCHIVE_AUTOCOMPLETE'
SETTING_DAYS = 'ARCHIVE_AUTOCOMPLETE_DAYS'
SETTING_HOURS = 'ARCHIVE_AUTOCOMPLETE_HOURS'


class AutocompleteResource(superdesk.Resource):
    item_methods = []
    resource_methods = ['GET']
    schema = {
        'value': {'type': 'string'},
    }


class AutocompleteService(superdesk.Service):

    allowed_fields = {
        'slugline',
    }

    def get(self, req, lookup):
        field = request.args.get('field', 'slugline')
        language = request.args.get('language', app.config.get('DEFAULT_LANGUAGE', 'en'))

        if not app.config.get(SETTING_ENABLED):
            raise SuperdeskApiError(_("Archive autocomplete is not enabled"), 404)

        if field not in self.allowed_fields:
            raise SuperdeskApiError(_("Field %(field)s is not allowed", field=field), 400)

        _filter = {
            'state': 'published',
            'language': language,
            'versioncreated': {'$gte': utcnow() - timedelta(
                days=app.config[SETTING_DAYS],
                hours=app.config[SETTING_HOURS],
            )},
        }
        values = self.backend._backend('archive').driver.db['archive'].distinct(field, _filter)
        sorted_values = sorted(values, key=locale.strxfrm)
        docs = [{'value': value} for value in sorted_values]
        return ListCursor(docs)


def init_app(_app):
    _app.client_config.update({'archive_autocomplete': _app.config.get(SETTING_ENABLED, False)})

    if _app.config.get(SETTING_ENABLED) and not _app.config.get(SETTING_HOURS) and not _app.config.get(SETTING_DAYS):
        warnings.warn(
            '{} is enabled but both {} and {} are not set.'.format(
                SETTING_ENABLED,
                SETTING_HOURS,
                SETTING_DAYS,
            )
        )

    superdesk.register_resource(
        'archive_autocomplete',
        AutocompleteResource,
        AutocompleteService,
        _app=_app)
