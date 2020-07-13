# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk.resource import Resource
from superdesk.services import BaseService
from .storage_destinations import StorageDestinationsResource, StorageDestinationsService
from .sets import SetsResource, SetsService
from sams_client import SamsClient
import superdesk
from flask_babel import _


def init_app(app):

    configs = {
        'HOST': app.config.get('SAMS_HOST'),
        'PORT': app.config.get('SAMS_PORT')
    }

    endpoint_name = StorageDestinationsResource.endpoint_name
    service = StorageDestinationsService(configs, datasource=endpoint_name, backend=superdesk.get_backend())
    StorageDestinationsResource(endpoint_name, app=app, service=service)
