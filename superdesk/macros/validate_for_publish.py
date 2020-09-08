# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk import get_resource_service, config
from superdesk.validation import ValidationError
from apps.publish.content.common import ITEM_PUBLISH
from flask_babel import lazy_gettext
import json


def validate_for_publish(item, **kwargs):
    doc = get_resource_service('archive').find_one(req=None, _id=item[config.ID_FIELD])
    validate_item = {'act': ITEM_PUBLISH, 'type': doc['type'], 'validate': doc}
    validation_errors = get_resource_service('validate').create([validate_item], fields=True)
    if validation_errors[0][0]:
        raise ValidationError(json.dumps(validation_errors[0][0]))

    return item


name = 'Validate for Publish'
label = lazy_gettext('Validate for Publish')
callback = validate_for_publish
access_type = 'frontend'
action_type = 'direct'
