# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2016 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk.resource import Resource
from superdesk.metadata.utils import item_url


class SuggestionsResource(Resource):
    """Resource used for live suggestions functionality."""

    item_url = item_url
    url = "suggestions/<{0}:item_id>".format(item_url)

    item_methods = ["GET"]
    privileges = {"GET": "archive"}
