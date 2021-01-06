# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from .media_references import MediaReferencesResource
from .media_editor import MediaEditorService, MediaEditorResource
from superdesk.services import BaseService
import superdesk


def init_app(app):
    endpoint_name = "media_references"
    service = BaseService(endpoint_name, backend=superdesk.get_backend())
    MediaReferencesResource(endpoint_name, app=app, service=service)

    endpoint_name = "media_editor"
    service = MediaEditorService(endpoint_name, backend=superdesk.get_backend())
    MediaEditorResource(endpoint_name, app=app, service=service)
