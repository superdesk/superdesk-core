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

from flask import request

from sams_client import SamsClient

from .utils import get_default_set_id_for_upload


def map_metadata_from_attachments(client: SamsClient, filename: str = None) -> Optional[Dict[str, Any]]:
    """Map request data for the `attachments` resource to SAMS Asset"""

    data = request.form.to_dict()

    if data.get('set_id'):
        # If the `set_id` attribute is set, this must be from the SAMS Attachments Widget
        return data
    elif data.get('title'):
        # Else if the `title` attribute is set, this must be from the standard Superdesk Attachments Widget
        return {
            'name': data.get('title'),
            'description': data.get('description'),
            'state': 'internal' if data.get('internal') else 'public',
            'filename': filename or data.get('title'),
            'set_id': get_default_set_id_for_upload(client, data)
        }

    return None
