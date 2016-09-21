# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2016 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


# must be imported for registration
import apps.analytics.engines.alchemy  # NOQA

engines = {}

def register_engine(name, engine):
    engines[name] = engine

def get_engine(name):
    return engines[name]
