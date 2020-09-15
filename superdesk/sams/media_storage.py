# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013-2020 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from typing import Dict, Callable, Any, BinaryIO, Union, Optional
import logging
from os import path

from eve.flaskapp import Eve
from eve.io.mongo.media import MediaStorage
from bson import ObjectId
from flask import current_app
from werkzeug.utils import secure_filename

from superdesk.factory.app import get_media_storage_class
from superdesk.storage.mimetype_mixin import MimetypeMixin
from superdesk.storage.superdesk_file import SuperdeskFile
from superdesk.attachments import RESOURCE as ATTACHMENTS_RESOURCE
from superdesk.sams import get_sams_client

from sams_client import SamsClient

from .metadata_resource_mapping import map_metadata_from_attachments
from .utils import get_asset_from_sams, get_file_from_sams, raise_sams_error

logger = logging.getLogger(__name__)


ResourceMappingFunction = Callable[
    [SamsClient, Optional[str]],
    Optional[Dict[str, Any]]
]
RESOURCE_METADATA_MAPPING: Dict[str, ResourceMappingFunction] = {
    ATTACHMENTS_RESOURCE: map_metadata_from_attachments
}


class SAMSMediaStorage(MediaStorage, MimetypeMixin):
    """SAMS MediaStorage implementation for Eve

    Uses SAMS if the requested resource exists in `RESOURCE_METADATA_MAPPING`
    Otherwise the fallback MediaStorage is used (`SuperdeskGridFSMediaStorage` or `AmazonMediaStorage`)
    """

    def __init__(self, app: Eve = None):
        super(SAMSMediaStorage, self).__init__(app or current_app)

        fallback_klass = get_media_storage_class(self.app.config, False)
        self._fallback = fallback_klass(self.app)
        self._client: SamsClient = get_sams_client(self.app)

    def get(
        self,
        id_or_filename: Union[ObjectId, str],
        resource: str = None,
        **kwargs
    ) -> SuperdeskFile:
        """Attempts to retrieve the file from SAMS or the `_fallback` provider"""

        if resource in RESOURCE_METADATA_MAPPING:
            file = get_file_from_sams(self._client, ObjectId(id_or_filename))
            if file:
                return file

        return self._fallback.get(
            id_or_filename,
            resource=resource,
            **kwargs
        )

    def put(
        self,
        content: BinaryIO,
        filename: str = None,
        content_type: str = None,
        resource: str = None,
        **kwargs: Dict[str, Any]
    ) -> ObjectId:
        """Attempts to upload the file to SAMS or the `_fallback` provider"""

        if resource in RESOURCE_METADATA_MAPPING:
            metadata = RESOURCE_METADATA_MAPPING[resource](
                self._client,
                secure_filename(path.basename(filename)) if filename else ''
            )

            if metadata is not None:
                response = self._client.assets.create(
                    docs=metadata,
                    files={'binary': content}
                )
                raise_sams_error(response)
                return response.json()['_id']

        return self._fallback.put(
            content,
            filename=filename,
            content_type=content_type,
            resource=resource,
            **kwargs
        )

    def delete(
        self,
        id_or_filename: Union[ObjectId, str],
        resource: str = None,
        **kwargs
    ):
        """Ignored if the file is stored in SAMS, otherwise deletes from the `_fallback` provider"""

        if resource in RESOURCE_METADATA_MAPPING:
            if get_asset_from_sams(self._client, ObjectId(id_or_filename)):
                # If the Asset exists in SAMS, then we should not delete it
                # as Assets should be deleted using DELETE /sams/assets/<id>
                return

        self._fallback.delete(
            id_or_filename,
            resource=resource,
            **kwargs
        )

    def exists(
        self,
        id_or_filename: Union[ObjectId, str],
        resource: str = None,
        **kwargs
    ) -> bool:
        """Returns True if the file is available in SAMS or the `_fallback` provider"""

        if resource in RESOURCE_METADATA_MAPPING:
            if get_asset_from_sams(self._client, ObjectId(id_or_filename)):
                return True

        return self._fallback.exists(
            id_or_filename,
            resource=resource,
            **kwargs
        )

    def __getattr__(self, name: Any) -> Any:
        """Returns `_fallback` attribute if not available in SAMSMediaStorage"""

        return self._fallback.__getattribute__(name)
