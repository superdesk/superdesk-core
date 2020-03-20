# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


import os
from superdesk.tests import TestCase
import ftplib
from apps.publish import init_app
from superdesk.publish.transmitters.ftp import FTPPublishService
import io
from unittest import mock


class NotFoundResponse():
    status_code = 404


class TestMedia(io.BytesIO):
    _id = 'media-id'
    filename = 'foo.txt'
    mimetype = 'text/plain'


def mockGet(self, _id, resource=None):
    return b'binary'


class FTPPublishTestCase(TestCase):
    def setUp(self):
        init_app(self.app)

    item = {'item_id': 'abc',
            'format': 'NITF',
            'formatted_item': '1234567890'}

    def is_item_loaded(self, url, uploaded_filename):
        config = FTPPublishService().config_from_url(url)
        with ftplib.FTP(config.get('host')) as ftp:
            ftp.login(config.get('username'), config.get('password'))
            ftp.cwd(config.get('path', ''))
            ftp.set_pasv(config.get('passive', False))

            for filename, facts in ftp.mlsd():
                if filename == uploaded_filename:
                    return True
            return False

    def test_it_can_connect(self):
        service = FTPPublishService()

        if 'FTP_URL' not in os.environ:
            return

        config = service.config_from_url(os.environ['FTP_URL'])
        self.item['destination'] = {'config': config}

        self.assertEqual('test', config['path'])
        self.assertEqual('localhost', config['host'])

        service._transmit(self.item, subscriber={'config': config})
        self.assertTrue(self.is_item_loaded(config, 'abc.ntf'))

    @mock.patch('ftplib.FTP', autospec=True)
    @mock.patch('superdesk.storage.SuperdeskGridFSMediaStorage.get', mockGet)
    def test_with_associations(self, mock_ftp_constructor, *args):
        item = {
            'associations': {
                'featuremedia': {
                    'renditions': {'16-9': {'poi': {'y': 1334, 'x': 2613},
                                            'href': '/5e422963a11fe98e697a8c84.jpg',
                                            'width': 1280, 'height': 720, 'mimetype': 'image/jpeg',
                                            'media': '5e422963a11fe98e697a8c84'},
                                   'original': {'poi': {'y': 1393, 'x': 2613},
                                                'href': '/5e422871a11fe98e697a8c27.jpg',
                                                'width': 4752, 'height': 3168, 'mimetype': 'image/jpeg',
                                                'media': '5e422871a11fe98e697a8c27'},
                                   '4-3': {'poi': {'y': 1393, 'x': 2114},
                                           'href': '/5e422962a11fe98e697a8c81.jpg',
                                           'width': 800, 'height': 600, 'mimetype': 'image/jpeg',
                                           'media': '5e422962a11fe98e697a8c81'}}}
            }}

        service = FTPPublishService()

        service._copy_published_media_files(item, mock_ftp_constructor)

        mock_ftp_constructor.storbinary.assert_any_call(cmd='STOR 5e422962a11fe98e697a8c81.jpg', fp=b'binary')
        mock_ftp_constructor.storbinary.assert_any_call(cmd='STOR 5e422963a11fe98e697a8c84.jpg', fp=b'binary')
        mock_ftp_constructor.storbinary.assert_any_call(cmd='STOR 5e422871a11fe98e697a8c27.jpg', fp=b'binary')

    @mock.patch('ftplib.FTP', autospec=True)
    @mock.patch('superdesk.storage.SuperdeskGridFSMediaStorage.get', mockGet)
    def test_with_association_and_embed(self, mock_ftp_constructor, *args):
        item = {
            'associations': {'featuremedia': {'renditions': {
                                              '16-9': {'media': '5e448ee9016d1f63a92f040b', 'width': 1280,
                                                       'href': '/5e448ee9016d1f63a92f040b.jpg',
                                                       'height': 720, 'mimetype': 'image/jpeg',
                                                       'poi': {'y': 1458, 'x': 1331}},
                                              '4-3': {'media': '5e448ee8016d1f63a92f0408', 'width': 800,
                                                      'href': '/5e448ee8016d1f63a92f0408.jpg',
                                                      'height': 600, 'mimetype': 'image/jpeg',
                                                      'poi': {'y': 1502, 'x': 1162}},
                                              'original': {'media': '5e448e47016d1f63a92f03b8', 'width': 5568,
                                                           'href': '/5e448e47016d1f63a92f03b8.jpg',
                                                           'height': 3712, 'mimetype': 'image/jpeg',
                                                           'poi': {'y': 1781, 'x': 1893}}}},
                             'editor_0': {'priority': 6,
                                          'subject': [{'code': '02000000', 'name': 'crime, law and justice'}],
                                          'body_text': 'pic alt', 'byline': 'The Great Unwashed', 'renditions': {
                                              '16-9': {'media': '5e448dd1016d1f63a92f039e', 'width': 1280,
                                                       'href': '/5e448dd1016d1f63a92f039e.png',
                                                       'height': 720, 'mimetype': 'image/png'},
                                              '4-3': {'media': '5e448dd1016d1f63a92f0398', 'width': 800,
                                                      'href': '/5e448dd1016d1f63a92f0398.png',
                                                      'height': 600, 'mimetype': 'image/png'},
                                              'original': {'media': '5e448dd1016d1f63a92f0393', 'width': 1615,
                                                           'href': '/upload-raw/5e448dd1016d1f63a92f0393.png',
                                                           'height': 1026, 'mimetype': 'image/png'}}}}}
        service = FTPPublishService()

        service._copy_published_media_files(item, mock_ftp_constructor)

        mock_ftp_constructor.storbinary.assert_any_call(cmd='STOR 5e448e47016d1f63a92f03b8.jpg', fp=b'binary')
        mock_ftp_constructor.storbinary.assert_any_call(cmd='STOR 5e448ee8016d1f63a92f0408.jpg', fp=b'binary')
        mock_ftp_constructor.storbinary.assert_any_call(cmd='STOR 5e448ee9016d1f63a92f040b.jpg', fp=b'binary')
        mock_ftp_constructor.storbinary.assert_any_call(cmd='STOR 5e448dd1016d1f63a92f0393.png', fp=b'binary')
        mock_ftp_constructor.storbinary.assert_any_call(cmd='STOR 5e448dd1016d1f63a92f0398.png', fp=b'binary')
        mock_ftp_constructor.storbinary.assert_any_call(cmd='STOR 5e448dd1016d1f63a92f039e.png', fp=b'binary')
