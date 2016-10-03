
import superdesk
from superdesk.metadata.item import ITEM_TYPE, CONTENT_TYPE, CONTENT_STATE, ITEM_STATE
from flask import render_template, render_template_string
from superdesk.errors import SuperdeskApiError
from eve.utils import config

PACKAGE_FIELDS = {
    'type', 'state', 'groups', 'unique_name', 'pubstatus', 'origina_creator', 'flags', 'guid',
    'schedule_settings', 'expiry', 'format', 'lock_time', 'lock_user', 'lock_session', config.ID_FIELD,
    config.LAST_UPDATED, config.DATE_CREATED, config.ETAG, 'version', '_current_version', 'version_creator',
    'operation', 'unique_id', 'version_created'
}


def get_template(highlightId):
    """Return the string template associated with highlightId or none"""
    if not highlightId:
        return None
    highlightService = superdesk.get_resource_service('highlights')
    highlight = highlightService.find_one(req=None, _id=highlightId)
    if not highlight or not highlight.get('template'):
        return None

    templateService = superdesk.get_resource_service('content_templates')
    template = templateService.find_one(req=None, _id=highlight.get('template'))
    return template


class GenerateHighlightsService(superdesk.Service):
    def create(self, docs, **kwargs):
        """Generate highlights text item for given package.

        If doc.preview is True it won't save the item, only return.
        """
        service = superdesk.get_resource_service('archive')
        for doc in docs:
            preview = doc.get('preview', False)
            package = service.find_one(req=None, _id=doc['package'])
            if not package:
                superdesk.abort(404)
            export = doc.get('export')
            template = get_template(package.get('highlight'))
            stringTemplate = None
            if template and 'body_html' in template.get('data', {}):
                stringTemplate = template['data']['body_html']

            doc.clear()
            doc[ITEM_TYPE] = CONTENT_TYPE.TEXT
            doc['family_id'] = package.get('guid')
            doc[ITEM_STATE] = CONTENT_STATE.SUBMITTED
            doc[config.VERSION] = 1

            for field in package:
                if field not in PACKAGE_FIELDS:
                    doc[field] = package[field]

            items = []
            for group in package.get('groups', []):
                for ref in group.get('refs', []):
                    if 'residRef' in ref:
                        item = service.find_one(req=None, _id=ref.get('residRef'))
                        if item:
                            if not (export or preview) and \
                                    (item.get('lock_session') or item.get('state') != 'published'):
                                message = 'Locked or not published items in highlight list.'
                                raise SuperdeskApiError.forbiddenError(message)

                            items.append(item)

            if stringTemplate:
                doc['body_html'] = render_template_string(stringTemplate, package=package, items=items)
            else:
                doc['body_html'] = render_template('default_highlight_template.txt', package=package, items=items)
        if preview:
            return [doc['body_html'] for doc in docs]
        else:
            return service.post(docs, **kwargs)


class GenerateHighlightsResource(superdesk.Resource):
    """Generate highlights item for given package."""

    schema = {
        'package': {
            # not setting relation here, we will fetch it anyhow
            'type': 'string',
            'required': True,
        },
        'preview': {
            'type': 'boolean',
            'default': False,
        },
        'export': {
            'type': 'boolean',
            'default': False,
        }
    }

    resource_methods = ['POST']
    item_methods = []
    privileges = {'POST': 'highlights'}
