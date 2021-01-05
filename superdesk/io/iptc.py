# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

"""IPTC module"""

import os
from superdesk import json
from datetime import datetime


def load_codes(filename):
    with open(filename, "r") as f:
        codes = json.load(f)
        return codes


dirname = os.path.dirname(os.path.realpath(__file__))
data_subject_codes = os.path.join(dirname, "data", "subject_codes.json")
subject_codes = load_codes(data_subject_codes)


def init_app(app):
    last_modified = datetime(2012, 7, 10)
    app.subjects.register(subject_codes, last_modified)
