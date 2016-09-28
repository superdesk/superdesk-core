
import superdesk

from flask import current_app as app
from superdesk.media.renditions import generate_renditions, get_renditions_spec
from apps.picture_crop import get_file


class PictureRenditionsService(superdesk.Service):
    """

    Create the renditions for the given `original` picture.

    """

    def create(self, docs, **kwargs):
        ids = []
        for doc in docs:
            item = doc.pop('item')
            orig = item['renditions']['original']
            orig_file = get_file(orig, item)
            rendition_spec = get_renditions_spec()
            inserted = []
            media_type, content_type = item['mimetype'].split('/')
            renditions = generate_renditions(orig_file, orig['media'], inserted, media_type,
                                             item['mimetype'], rendition_spec, app.media.url_for_media)
            doc['renditions'] = renditions
            ids.append(item['_id'])
        return ids


class PictureRenditionsResource(superdesk.Resource):
    item_methods = []
    resource_methods = ['POST']
    privileges = {'POST': 'archive'}
    schema = {
        'item': {'type': 'dict', 'required': True},
    }


def init_app(app):
    superdesk.register_resource(
        'picture_renditions',
        PictureRenditionsResource,
        PictureRenditionsService,
        'archive')
