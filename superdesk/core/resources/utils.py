# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2024 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from .model import ResourceModel
from .fields import ObjectId


def resource_uses_objectid_for_id(data_class: type[ResourceModel]) -> bool:
    try:
        return data_class.model_fields["id"].annotation == ObjectId
    except KeyError:
        return False
