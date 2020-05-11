
import superdesk

from flask import current_app as app, json
from superdesk.utils import get_random_string
from superdesk.media.media_operations import crop_image, process_image, encode_metadata
from apps.search_providers.proxy import PROXY_ENDPOINT
from superdesk.media.image import fix_orientation


def get_file(rendition, item):
    if item.get('fetch_endpoint'):
        if item['fetch_endpoint'] == PROXY_ENDPOINT:  # it requires provider info
            return superdesk.get_resource_service(item['fetch_endpoint']).fetch_rendition(rendition, item=item)
        return superdesk.get_resource_service(item['fetch_endpoint']).fetch_rendition(rendition)
    else:
        return app.media.fetch_rendition(rendition)


def get_crop_size(crop, width=800, height=600):
    """In case width or height is missing it will do the math.

    :param size: size dict with `width` or `height`
    :param crop: crop specs
    :param width: original width
    :param height: original height
    """
    if not ('CropRight' in crop and 'CropLeft' in crop and 'CropBottom' in crop and 'CropTop' in crop):
        crop['CropRight'] = width
        crop['CropLeft'] = 0
        crop['CropBottom'] = height
        crop['CropTop'] = 0

        return {
            'width': width,
            'height': height
        }

    crop_width = crop['CropRight'] - crop['CropLeft']
    crop_height = crop['CropBottom'] - crop['CropTop']

    size = {
        'width': crop.get('width', crop_width),
        'height': crop.get('height', crop_height)
    }

    crop_ratio = crop_width / crop_height
    size_ratio = size['width'] / size['height']

    # Keep crop data proportional to the size provided
    # i.e. if the rendition is 4x3, make sure the crop data is also a 4x3 aspect ratio
    # but make sure it won't exceed picture boundaries
    if round(crop_ratio, 2) > round(size_ratio, 2):
        crop_width = int(crop_height * size_ratio)
        crop['CropRight'] = crop['CropLeft'] + crop_width
    elif round(crop_ratio, 2) < round(size_ratio, 2):
        crop_height = int(crop_width / size_ratio)
        crop['CropBottom'] = crop['CropTop'] + crop_height

    return size


class PictureCropService(superdesk.Service):
    """Crop original image of picture item and return its url.

    It is used for embedded images within text item body.
    """

    def create(self, docs, **kwargs):
        ids = []
        for doc in docs:
            item = doc.pop('item')
            crop = doc.pop('crop')
            orig = item['renditions']['original']
            size = get_crop_size(crop, orig.get('width', 800), orig.get('height', 600))
            orig_file = get_file(orig, item)
            filename = get_random_string()
            ok, output = crop_image(orig_file, filename, crop, size)
            if ok:
                metadata = encode_metadata(process_image(orig_file))
                metadata.update({'length': json.dumps(len(output.getvalue()))})
                output = fix_orientation(output)
                media = app.media.put(output, filename, orig['mimetype'], metadata=metadata)
                doc['href'] = app.media.url_for_media(media, orig['mimetype'])
                doc['width'] = output.width
                doc['height'] = output.height
                ids.append(media)
        return ids


class PictureCropResource(superdesk.Resource):

    item_methods = []
    resource_methods = ['POST']
    privileges = {'POST': 'archive'}

    schema = {
        'item': {'type': 'dict', 'required': True, 'empty': False},
        'crop': {'type': 'dict', 'required': True, 'empty': False},
        'href': {'type': 'string', 'readonly': True},
        'width': {'type': 'integer', 'readonly': True},
        'height': {'type': 'integer', 'readonly': True},
    }


def init_app(app):
    superdesk.register_resource(
        'picture_crop',
        PictureCropResource,
        PictureCropService,
        'archive')
