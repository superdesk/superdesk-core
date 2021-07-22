# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013-2020 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from typing import Dict, Any, Optional

from bson import ObjectId
from eve.utils import str_to_date
from requests import Response
from requests.exceptions import HTTPError

from superdesk.errors import SuperdeskApiError
from superdesk.storage.superdesk_file import SuperdeskFile
from sams_client import SamsClient


class SAMSFileWrapper(SuperdeskFile):
    """Helper class to convert SAMS Asset Binary response to file-like object"""

    def __init__(self, asset: Dict[str, Any], file: Response):
        super().__init__()
        self.write(file.content)
        self.seek(0)
        self.content_type = asset["mimetype"]
        self.length = asset["length"]
        self._name = asset["name"]
        self.filename = asset["filename"]
        self.upload_date = str_to_date(asset["_updated"])
        self.md5 = asset["_etag"]
        self._id = asset["_id"]


def get_asset_from_sams(client: SamsClient, asset_id: ObjectId) -> Optional[Dict[str, Any]]:
    """Attempts to retrieve an Asset from SAMS"""

    response = client.assets.get_by_id(asset_id)

    if response.status_code == 404:
        return None

    raise_sams_error(response)
    return response.json()


def get_file_from_sams(client: SamsClient, asset_id: ObjectId) -> Optional[SAMSFileWrapper]:
    """Attempts to retrieve the Asset Binary from SAMS"""

    asset = get_asset_from_sams(client, asset_id)

    if asset:
        response = client.assets.get_binary_by_id(asset_id)

        # If the Asset exists in SAMS, then so should the file
        raise_sams_error(response)

        return SAMSFileWrapper(asset, response)

    return None


def get_asset_public_url(client: SamsClient, asset_id: ObjectId) -> Optional[str]:
    """Attempts to retrieve the public URL for the Asset"""

    asset = get_asset_from_sams(client, asset_id)

    if asset:
        return (asset["_links"].get("public") or {}).get("href")

    return None


def get_default_set_id_for_upload(client: SamsClient, data: Dict[str, Any]) -> ObjectId:
    """Returns the Set ID to use for a file upload"""

    if not data.get("set_id"):
        # TODO: Implement default sets for Desk/Module (i.e. Planning)
        #       For now, simply return the first Set found
        response = client.sets.search(params={"max_results": 1})
        raise_sams_error(response)
        set_item = response.json()["_items"][0]
        return ObjectId(set_item["_id"])

    return ObjectId(data["set_id"])


def raise_sams_error(response: Response):
    """If an error was raised from SAMS, attempts to re-raise it as a Superdesk error

    Raising Superdesk errors are to be used outside the SAMS workspace functionality
    i.e. with the Eve MediaStorage provider functionality
    """

    try:
        response.raise_for_status()
    except HTTPError as http_error:
        error = response.json()
        raise SuperdeskApiError(
            status_code=response.status_code,
            message=error.get("description") or "",
            payload=error,
            exception=http_error,
        )
