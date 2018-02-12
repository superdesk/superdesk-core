
import os


def get_picture_fixture(filename='iphone_gpsinfo_exif.JPG'):
    """Get picture file path."""
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), 'fixtures', filename)
