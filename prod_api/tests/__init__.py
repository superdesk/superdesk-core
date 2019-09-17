# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2019 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk.tests import TestCase as _TestCase

from prod_api.app import get_app


class TestCase(_TestCase):

    def setUp(self):
        super().setUp()

        test_config = {
            'DEBUG': self.app.config['DEBUG'],
            'TESTING': self.app.config['TESTING'],
            'SUPERDESK_TESTING': self.app.config['SUPERDESK_TESTING'],
            'MONGO_CONNECT': self.app.config['MONGO_CONNECT'],
            'MONGO_MAX_POOL_SIZE': self.app.config['MONGO_MAX_POOL_SIZE'],
            'MONGO_URI': self.app.config['MONGO_URI'],
            'ELASTICSEARCH_INDEX': self.app.config['ELASTICSEARCH_INDEX'],
        }

        self.prodapi = get_app(test_config)
