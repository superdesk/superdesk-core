
import os
import tempfile

from PIL import Image
from superdesk.tests import TestCase
from superdesk.media.renditions import generate_renditions, get_renditions_spec

IMG_PATH = os.path.join(os.path.dirname(__file__), 'fixtures', 'iphone_gpsinfo_exif.JPG')
BIG_IMG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    'features', 'steps', 'fixtures', 'bike.jpg',
)


class GenerateRenditionsTestCase(TestCase):

    def setUp(self):
        self.app.data.insert('vocabularies', [
            {
                '_id': 'crop_sizes',
                'items': [
                    {'is_active': True, 'name': 'landscape', 'width': 200, 'height': 100},
                    {'is_active': True, 'name': 'portrait', 'width': 150, 'height': 200},
                ],
            },
        ])

    def save_binary(self, rendition):
        """Used while debugging to check the picture."""
        binary = self.app.media.get(rendition['media'])
        image = Image.open(binary)
        fd, path = tempfile.mkstemp('.jpg')
        with open(fd, 'w') as out:
            image.save(out, 'jpeg')
            print('saved', path)

    def test_generate_renditions_custom_crop(self):
        inserted = []
        renditions = get_renditions_spec()
        with open(IMG_PATH, 'rb') as original:
            generated = generate_renditions(original, 'id', inserted, 'image', 'image/jpeg', renditions,
                                            self.app.media.url_for_media)

        # thumbnail should keep 4:3 ration
        self.assertIn('thumbnail', generated)
        self.assertEqual(160, generated['thumbnail']['width'])
        self.assertEqual(120, generated['thumbnail']['height'])

        # landscape should be cropped to 200x100
        self.assertIn('landscape', generated)
        landscape = generated['landscape']
        self.assertEqual(200, landscape['width'])
        self.assertEqual(100, landscape['height'])
        self.assertEqual(0, landscape['CropLeft'])
        self.assertEqual(400, landscape['CropRight'])
        self.assertEqual(50, landscape['CropTop'])
        self.assertEqual(250, landscape['CropBottom'])

        # portrait should be cropped to 150x200
        self.assertIn('portrait', generated)
        portrait = generated['portrait']
        self.assertEqual(150, portrait['width'])
        self.assertEqual(200, portrait['height'])
        self.assertEqual(0, portrait['CropTop'])
        self.assertEqual(300, portrait['CropBottom'])
        self.assertEqual(87, portrait['CropLeft'])
        self.assertEqual(312, portrait['CropRight'])

    def test_generate_renditions_base_image(self):
        inserted = []
        renditions = get_renditions_spec()
        with open(BIG_IMG_PATH, 'rb') as original:
            generated = generate_renditions(original, 'id', inserted, 'image', 'image/jpeg', renditions,
                                            self.app.media.url_for_media)

        self.assertIn('landscape', generated)
        landscape = generated['landscape']
        self.assertEqual(200, landscape['width'])
        self.assertEqual(100, landscape['height'])
        self.assertEqual(0, landscape['CropLeft'])
        self.assertEqual(1200, landscape['CropRight'])
        self.assertEqual(500, landscape['CropTop'])
        self.assertEqual(1100, landscape['CropBottom'])
