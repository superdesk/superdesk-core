# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import json
import os
from superdesk.locators.locators import LocatorIndex, bp
import superdesk


def _load_json(file_path):
    """
    Reads JSON string from the file located in file_path.

    :param file_path: path of the file having JSON string.
    :return: JSON Object
    """
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def init_app(app):
    app.locators = LocatorIndex()
    superdesk.blueprint(bp, app)
    _locators_file_path = app.config.get(
        "LOCATORS_DATA_FILE", os.path.join(os.path.dirname(os.path.realpath(__file__)), "data", "locators.json")
    )
    app.locators.register(_load_json(_locators_file_path))
