# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license
import json

from eve.utils import ParsedRequest

import superdesk
import logging
from copy import deepcopy
from superdesk import get_resource_service, config
from superdesk.errors import SuperdeskApiError
from superdesk.media.media_operations import crop_image, process_file_from_stream
from superdesk.upload import url_for_media
from superdesk.metadata.item import CONTENT_TYPE, ITEM_TYPE, MEDIA_TYPES, ASSOCIATIONS
from.renditions import _resize_image


logger = logging.getLogger(__name__)


class CropService():

    crop_sizes = []

    def validate_crop(self, original, updates, crop_name):
        """Validate crop info on media item.

        :param dict original: original item
        :param dict updates: updated renditions
        :param str crop_name: name of the crop
        :param dict doc: crop co-ordinates
        :raises SuperdeskApiError.badRequestError:
            For following conditions:
            1) if type != picture
            2) if renditions are missing in the original image
            3) if original rendition is missing
            4) Crop name is invalid
        """
        # Check if type is picture
        if original[ITEM_TYPE] != CONTENT_TYPE.PICTURE:
            raise SuperdeskApiError.badRequestError(message='Only images can be cropped!')

        # Check if the renditions exists
        if not original.get('renditions'):
            raise SuperdeskApiError.badRequestError(message='Missing renditions!')

        # Check if the original rendition exists
        if not original.get('renditions').get('original'):
            raise SuperdeskApiError.badRequestError(message='Missing original rendition!')

        # Check if the crop name is valid
        crop = self.get_crop_by_name(crop_name)
        crop_data = updates.get('renditions', {}).get(crop_name, {})
        if not crop and 'CropLeft' in crop_data:
            raise SuperdeskApiError.badRequestError(message='Unknown crop name! (name=%s)' % crop_name)

        self._validate_values(crop_data)
        self._validate_poi(original, updates, crop_name)
        self._validate_aspect_ratio(crop, crop_data)

    def _validate_values(self, crop):
        int_fields = ('CropLeft', 'CropTop', 'CropRight', 'CropBottom', 'width', 'height')
        for field in int_fields:
            if field in crop:
                try:
                    crop[field] = int(crop[field])
                except (TypeError, ValueError):
                    raise SuperdeskApiError.badRequestError('Invalid value for %s in renditions' % field)

    def _validate_poi(self, original, updates, crop_name):
        """Validate the crop point of interest in the renditions dictionary for the given crop

        :param dict original: original item
        :param dict updates: updated renditions
        """
        renditions = original.get('renditions', {})
        updated_renditions = updates.get('renditions', {})
        original_image = deepcopy(renditions['original'])
        original_image.update(updated_renditions.get('original', {}))
        if 'poi' in updates:
            if 'x' not in updates['poi'] or 'y' not in updates['poi']:
                del updates['poi']
                return
            poi = updates['poi']
        elif 'poi' not in original:
            return
        else:
            if crop_name not in updated_renditions:
                return
            poi = original['poi']

        crop_data = updated_renditions[crop_name] if crop_name in updated_renditions else renditions[crop_name]
        orig_poi_x = int(original_image['width'] * poi['x'])
        orig_poi_y = int(original_image['height'] * poi['y'])

        if orig_poi_y < crop_data.get('CropTop', 0) \
                or orig_poi_y > crop_data.get('CropBottom', original_image['height']) \
                or orig_poi_x < crop_data.get('CropLeft', 0) \
                or orig_poi_x > crop_data.get('CropRight', original_image['width']):
            raise SuperdeskApiError('Point of interest outside the crop %s limits' % crop_name)

    def _validate_aspect_ratio(self, crop, doc):
        """Checks if the aspect ratio is consistent with one in defined in spec

        :param crop: Spec parameters
        :param doc: Posted parameters
        :raises SuperdeskApiError.badRequestError:
        """
        if 'CropLeft' not in doc:
            return

        width = doc['CropRight'] - doc['CropLeft']
        height = doc['CropBottom'] - doc['CropTop']
        if not (crop.get('width') or crop.get('height') or crop.get('ratio')):
            raise SuperdeskApiError.badRequestError(
                message='Crop data are missing. width, height or ratio need to be defined')
        if crop.get('width') and crop.get('height'):
            expected_crop_width = int(crop['width'])
            expected_crop_height = int(crop['height'])
            if width < expected_crop_width or height < expected_crop_height:
                raise SuperdeskApiError.badRequestError(
                    message='Wrong crop size. Minimum crop size is {}x{}.'.format(crop['width'], crop['height']))
                doc_ratio = round(width / height, 1)
                spec_ratio = round(expected_crop_width / expected_crop_height, 1)
                if doc_ratio != spec_ratio:
                    raise SuperdeskApiError.badRequestError(message='Wrong aspect ratio!')
        elif crop.get('ratio'):
            ratio = crop.get('ratio')
            if type(ratio) not in [int, float]:
                ratio = ratio.split(':')
                ratio = int(ratio[0]) / int(ratio[1])
            if abs((width / height) - ratio) > 0.1:
                raise SuperdeskApiError.badRequestError(
                    message='Ratio %s is not respected. We got %f' % (crop.get('ratio'), abs((width / height))))

    def get_crop_by_name(self, crop_name):
        """Finds the crop in the list of crops by name

        :param crop_name: Crop name
        :return: Matching crop or None
        """
        if not self.crop_sizes:
            self.crop_sizes = get_resource_service('vocabularies').find_one(req=None, _id='crop_sizes').get('items')

        if not self.crop_sizes:
            raise SuperdeskApiError.badRequestError(message='Crops sizes couldn\'t be loaded!')

        return next((c for c in self.crop_sizes if c.get('name', '').lower() == crop_name.lower()), None)

    def create_crop(self, original_image, crop_name, crop_data):
        """Create a new crop based on the crop co-ordinates

        :param original: Article to add the crop
        :param crop_name: Name of the crop
        :param doc: Crop details
        :raises SuperdeskApiError.badRequestError
        :return dict: rendition
        """
        original_file = superdesk.app.media.fetch_rendition(original_image)
        if not original_file:
            raise SuperdeskApiError.badRequestError('Original file couldn\'t be found')
        try:
            cropped, out = crop_image(original_file, crop_name, crop_data)
            crop = self.get_crop_by_name(crop_name)
            if not cropped:
                raise SuperdeskApiError.badRequestError('Saving crop failed.')
            # resize if needed
            if crop.get('width') or crop.get('height'):
                out, width, height = _resize_image(out,
                                                   size=(crop.get('width'), crop.get('height')),
                                                   keepProportions=crop.get('keep_proportions', True))
                crop['width'] = width
                crop['height'] = height
                out.seek(0)
            return self._save_cropped_image(out, original_image, crop_data)
        except SuperdeskApiError:
            raise
        except Exception as ex:
            raise SuperdeskApiError.badRequestError('Generating crop failed: {}'.format(str(ex)))

    def _save_cropped_image(self, file_stream, original, doc):
        """Saves the cropped image and returns the crop dictionary

        :param file_stream: cropped image stream
        :param original: original rendition
        :param doc: crop data
        :return dict: Crop values
        :raises SuperdeskApiError.internalError
        """
        crop = {}
        try:
            file_name, content_type, metadata = process_file_from_stream(file_stream,
                                                                         content_type=original.get('mimetype'))
            file_stream.seek(0)
            file_id = superdesk.app.media.put(file_stream, filename=file_name,
                                              content_type=content_type,
                                              resource='upload',
                                              metadata=metadata)
            crop['media'] = file_id
            crop['mimetype'] = content_type
            crop['href'] = url_for_media(file_id, content_type)
            crop['CropTop'] = doc.get('CropTop', None)
            crop['CropLeft'] = doc.get('CropLeft', None)
            crop['CropRight'] = doc.get('CropRight', None)
            crop['CropBottom'] = doc.get('CropBottom', None)
            return crop
        except Exception as ex:
            try:
                superdesk.app.media.delete(file_id)
            except Exception:
                pass
            raise SuperdeskApiError.internalError('Generating crop failed: {}'.format(str(ex)), exception=ex)

    def _delete_crop_file(self, file_id):
        """Delete the crop file

        :param Object_id file_id: Object_Id of the file.
        """
        try:
            superdesk.app.media.delete(file_id)
        except Exception:
            logger.exception("Crop File cannot be deleted. File_Id {}".format(file_id))

    def create_multiple_crops(self, updates, original):
        """Create multiple crops based on the renditions.

        :param dict updates: update item
        :param dict original: original of the updated item
        """
        if original.get(ITEM_TYPE) != CONTENT_TYPE.PICTURE:
            return

        update_renditions = updates.get('renditions', {})
        renditions = deepcopy(original.get('renditions', {}))
        # keep renditions updates (urls may have changed)
        renditions.update(update_renditions)
        renditions = {k: renditions[k] for k in renditions if renditions[k]}

        if 'original' in updates.get('renditions', {}):
            original_image = updates['renditions']['original']
        else:
            try:
                original_image = original['renditions']['original']
            except KeyError:
                return

        for key in [k for k in update_renditions if update_renditions[k]]:
            if not self.get_crop_by_name(key):
                continue

            original_crop = original.get('renditions', {}).get(key, {})
            fields = ('CropLeft', 'CropTop', 'CropRight', 'CropBottom')
            crop_data = update_renditions.get(key, {})
            if any(crop_data.get(name) != original_crop.get(name) for name in fields) and not crop_data.get('media'):
                rendition = self.create_crop(original_image, key, crop_data)
                renditions[key] = rendition

        poi = updates.get('poi')
        if poi:
            for crop_name in renditions:
                self._set_crop_poi(renditions, crop_name, poi)

        updates['renditions'] = renditions

    def _set_crop_poi(self, renditions, crop_name, poi):
        """Set the crop point of interest in the renditions dictionary for the given crop

        :param dict renditions: updated renditions
        :param string crop_name: the crop for which to set the poi
        :param dict poi: the point of interest dictionary
        """
        fields = ('CropLeft', 'CropTop', 'CropRight', 'CropBottom')
        if 'x' in poi and 'y' in poi:
            original_image = renditions['original']
            crop_data = renditions[crop_name]
            orig_poi_x = int(original_image['width'] * poi['x'])
            orig_poi_y = int(original_image['height'] * poi['y'])

            if any(name in crop_data for name in fields):
                crop_poi_x = orig_poi_x - crop_data.get('CropLeft', 0)
                crop_poi_y = orig_poi_y - crop_data.get('CropTop', 0)
            else:
                crop_poi_x = int(crop_data.get('width', original_image['width']) * poi['x'])
                crop_poi_y = int(crop_data.get('height', original_image['height']) * poi['y'])
            renditions[crop_name]['poi'] = {'x': crop_poi_x, 'y': crop_poi_y}

    def validate_multiple_crops(self, updates, original):
        """Validate crops for the image

        :param dict updates: update item
        :param dict original: original of the updated item
        """
        renditions = updates.get('renditions', {})
        if not (renditions and original.get(ITEM_TYPE) == CONTENT_TYPE.PICTURE):
            return

        for key in [k for k in renditions if renditions[k]]:
            self.validate_crop(original, updates, key)

    def delete_replaced_crop_files(self, updates, original):
        """Delete the replaced crop files.

        :param dict updates: update item
        :param dict original: original of the updated item
        """
        update_renditions = updates.get('renditions', {})
        if original.get(ITEM_TYPE) == CONTENT_TYPE.PICTURE and update_renditions:
            renditions = original.get('renditions', {})
            for key in update_renditions:
                if self.get_crop_by_name(key) and \
                        update_renditions.get(key, {}).get('media') != \
                        renditions.get(key, {}).get('media'):
                    self._delete_crop_file(renditions.get(key, {}).get('media'))

    def update_media_references(self, updates, original, published=False):
        """Update the media references collection.
         When item (media item or associated media) is updated or created,
         media_references are created. These media_references are updated to published state
         once the item is published.

        :param dict updates: Updates of the item
        :param dict original: Original item
        :param boolean published: True if publishing the item else False
        """
        item_id = original.get(config.ID_FIELD)
        references = {}
        if updates.get('renditions', original.get('renditions', {})):
            references = {
                item_id: updates.get('renditions', original.get('renditions', {}))
            }

        if original.get(ITEM_TYPE) not in MEDIA_TYPES:
            associations = updates.get(ASSOCIATIONS) or original.get(ASSOCIATIONS)
            if not associations:
                return

            references = {assoc.get(config.ID_FIELD): assoc.get('renditions')
                          for assoc in associations.values() if assoc and assoc.get('renditions')}

        if not references:
            return

        for assoc_id, renditions in references.items():
            associated_id = assoc_id if assoc_id != item_id else None
            for rendition in [r for r in renditions.values() if r]:
                if not rendition.get('media'):
                    continue

                media = str(rendition.get('media'))
                reference = get_resource_service('media_references').find_one(req=None, item_id=item_id,
                                                                              media_id=media)
                if not reference:
                    try:
                        get_resource_service('media_references').post([{'item_id': item_id,
                                                                        'media_id': media,
                                                                        'associated_id': associated_id,
                                                                        'published': False}])
                    except Exception:
                        logger.exception('Failed to insert media reference item {} media {}'.format(item_id, media))

        # item is publish
        if not published:
            return

        req = ParsedRequest()
        req.where = json.dumps({'item_id': item_id, 'published': False})
        refs = list(get_resource_service('media_references').get(req=req, lookup=None))
        for ref in refs:
            try:
                get_resource_service('media_references').patch(ref.get(config.ID_FIELD),
                                                               updates={'published': True})
            except Exception:
                logger.exception('Failed to update media '
                                 'reference item {} media {}'.format(ref.get("item_id"), ref.get("media_id")))
