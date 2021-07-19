# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2019 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from eve import Eve


def init_app(app: Eve):
    """Initialize the `planning`, `events` and `assignments` API endpoints

    None of the endpoints are registered if `superdesk-planning` is not installed
    """

    try:
        from planning.prod_api import init_app as init_planning_app

        init_planning_app(app)
    except ImportError:
        pass
