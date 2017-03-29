
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
            no_custom_crops = doc.get('no_custom_crops', False)
            rendition_spec = get_renditions_spec(no_custom_crops=no_custom_crops)
            inserted = []
            mimetype = item.get('mimetype', orig.get('mimetype', '/'))
            media_type, content_type = mimetype.split('/')
            renditions = generate_renditions(orig_file, orig['media'], inserted, media_type,
                                             mimetype, rendition_spec, app.media.url_for_media)
            doc['renditions'] = renditions
            ids.append(item['_id'])
        return ids


class PictureRenditionsResource(superdesk.Resource):
    item_methods = []
    resource_methods = ['POST']
    privileges = {'POST': 'archive'}
    schema = {
        'item': {'type': 'dict', 'required': True},
        'no_custom_crops': {'type': 'boolean'}
    }


def init_app(app):
    superdesk.register_resource(
        'picture_renditions',
        PictureRenditionsResource,
        PictureRenditionsService,
        'archive')
