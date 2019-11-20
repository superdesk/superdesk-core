
import locale
import superdesk

from flask import current_app as app, request
from datetime import timedelta
from superdesk.utils import ListCursor
from superdesk.utc import utcnow
from superdesk.errors import SuperdeskApiError


class AutocompleteResource(superdesk.Resource):
    item_methods = []
    resource_methods = ['GET']


class AutocompleteService(superdesk.Service):

    allowed_fields = {
        'slugline',
    }

    def get(self, req, lookup):
        field = request.args.get('field', 'slugline')
        language = request.args.get('language', app.config.get('DEFAULT_LANGUAGE', 'en'))

        if not app.config.get('ARCHIVE_AUTOCOMPLETE'):
            raise SuperdeskApiError("Archive autocomplete is not enabled", 404)

        if field not in self.allowed_fields:
            raise SuperdeskApiError("Field {} is not allowed".format(field), 400)

        _filter = {
            'state': 'published',
            'language': language,
            'versioncreated': {'$gte': utcnow() - timedelta(
                days=app.config['ARCHIVE_AUTOCOMPLETE_DAYS'],
                hours=app.config['ARCHIVE_AUTOCOMPLETE_HOURS'],
            )},
        }
        values = self.backend._backend('archive').driver.db['archive'].distinct(field, _filter)
        sorted_values = sorted(values, key=locale.strxfrm)
        docs = [{'value': value} for value in sorted_values]
        return ListCursor(docs)


def init_app(_app):
    _app.client_config.update({'archive_autocomplete': _app.config.get('ARCHIVE_AUTOCOMPLETE', False)})
    superdesk.register_resource(
        'archive_autocomplete',
        AutocompleteResource,
        AutocompleteService,
        _app=_app)
