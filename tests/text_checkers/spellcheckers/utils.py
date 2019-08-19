# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013 - 2019 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

"""This module contains common tools for spellchecker tests"""

from unittest.mock import MagicMock
from superdesk import get_resource_service


def mock_dictionaries(service, model):
    """A side effect to return a mocked dictionaries service

    other services are returned normally
    """
    if service == 'dictionaries':
        fake_service = MagicMock()
        fake_service.get_model_for_lang.return_value = model
        return fake_service
    else:
        return get_resource_service(service)
