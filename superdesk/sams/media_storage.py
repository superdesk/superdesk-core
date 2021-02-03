# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013-2020 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from typing import Dict, Any, BinaryIO, Union
import logging
from os import path

from eve.flaskapp import Eve
from eve.io.mongo.media import MediaStorage
from bson import ObjectId
from flask import current_app, request
from werkzeug.utils import secure_filename

from superdesk.factory.app import get_media_storage_class
from superdesk.default_settings import strtobool
from superdesk.storage.mimetype_mixin import MimetypeMixin
from superdesk.storage.superdesk_file import SuperdeskFile
from superdesk.attachments import RESOURCE as ATTACHMENTS_RESOURCE
from superdesk.sams import get_sams_client

from sams_client import SamsClient

from .utils import (
    get_asset_from_sams,
    get_file_from_sams,
    raise_sams_error,
    get_default_set_id_for_upload,
    get_asset_public_url,
)

logger = logging.getLogger(__name__)


SAMS_RESOURCE_ENABLED: Dict[str, bool] = {ATTACHMENTS_RESOURCE: True}


def get_sams_values_from_resource_schema(resource: str, data: Dict[str, Any]):
    schema = current_app.config["DOMAIN"][resource]["schema"]

    def _get_field(field: str):
        sams_mapping = (schema.get(field) or {}).get("sams") or {}
        return sams_mapping.get("field") or field

    def _get_value(field: str):
        value_type = (schema.get(field) or {}).get("type")
        sams_mapping = (schema.get(field) or {}).get("sams") or {}
        data_value = data[field]

        if value_type == "boolean" and isinstance(data_value, str):
            data_value = strtobool(data_value)

        return (sams_mapping.get("map_value") or {}).get(data_value) or data_value

    return {_get_field(field): _get_value(field) for field in data.keys()}


class SAMSMediaStorage(MediaStorage, MimetypeMixin):
    """SAMS MediaStorage implementation for Eve

    Uses SAMS if the requested resource exists in `SAMS_RESOURCE_ENABLED`
    Otherwise the fallback MediaStorage is used (`SuperdeskGridFSMediaStorage` or `AmazonMediaStorage`)
    """

    def __init__(self, app: Eve = None):
        super(SAMSMediaStorage, self).__init__(app or current_app)

        fallback_klass = get_media_storage_class(self.app.config, False)
        self._fallback = fallback_klass(self.app)
        self._client: SamsClient = get_sams_client(self.app)

    def url_for_external(self, media_id: str, resource: str = None) -> str:
        """Returns a URL for external use

        Returns a URL for use with the SAMS FileServer (if the Asset is public),
        otherwise falls back to the Content/Production API (via MediaStorage fallback)

        :param str media_id: The ID of the asset
        :param str resource: The name of the resource type this Asset is attached to
        :rtype: str
        :return: The URL for external use
        """

        if resource is not None and SAMS_RESOURCE_ENABLED.get(resource, False):
            url = get_asset_public_url(self._client, ObjectId(media_id))

            if url:
                # If SAMS provided a public URL, return that
                # otherwise return a href for Production/Content API instead
                return url

        return self._fallback.url_for_external(media_id)

    def get(self, id_or_filename: Union[ObjectId, str], resource: str = None, **kwargs) -> SuperdeskFile:
        """Attempts to retrieve the file from SAMS or the `_fallback` provider"""

        if resource is not None and SAMS_RESOURCE_ENABLED.get(resource, False):
            file = get_file_from_sams(self._client, ObjectId(id_or_filename))
            if file:
                return file

        return self._fallback.get(id_or_filename, resource=resource, **kwargs)

    def put(
        self,
        content: BinaryIO,
        filename: str = None,
        content_type: str = None,
        resource: str = None,
        **kwargs: Dict[str, Any],
    ) -> ObjectId:
        """Attempts to upload the file to SAMS or the `_fallback` provider"""

        if resource is not None and SAMS_RESOURCE_ENABLED.get(resource, False):
            data = request.form.to_dict()
            metadata = get_sams_values_from_resource_schema(resource, data)

            if not metadata.get("set_id"):
                metadata["set_id"] = get_default_set_id_for_upload(self._client, data)
            if not metadata.get("state"):
                metadata["state"] = "public"
            if not metadata.get("filename"):
                metadata["filename"] = secure_filename(path.basename(filename)) if filename else ""

            response = self._client.assets.create(docs=metadata, files={"binary": content})
            raise_sams_error(response)
            return response.json()["_id"]

        return self._fallback.put(content, filename=filename, content_type=content_type, resource=resource, **kwargs)

    def delete(self, id_or_filename: Union[ObjectId, str], resource: str = None, **kwargs):
        """Ignored if the file is stored in SAMS, otherwise deletes from the `_fallback` provider"""

        if resource is not None and SAMS_RESOURCE_ENABLED.get(resource, False):
            if get_asset_from_sams(self._client, ObjectId(id_or_filename)):
                # If the Asset exists in SAMS, then we should not delete it
                # as Assets should be deleted using DELETE /sams/assets/<id>
                return

        self._fallback.delete(id_or_filename, resource=resource, **kwargs)

    def exists(self, id_or_filename: Union[ObjectId, str], resource: str = None, **kwargs) -> bool:
        """Returns True if the file is available in SAMS or the `_fallback` provider"""

        if resource is not None and SAMS_RESOURCE_ENABLED.get(resource, False):
            if get_asset_from_sams(self._client, ObjectId(id_or_filename)):
                return True

        return self._fallback.exists(id_or_filename, resource=resource, **kwargs)

    def __getattr__(self, name: Any) -> Any:
        """Returns `_fallback` attribute if not available in SAMSMediaStorage"""

        return self._fallback.__getattribute__(name)
