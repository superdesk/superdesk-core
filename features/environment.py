# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import os
from superdesk import tests
from superdesk.io.tests import setup_providers, teardown_providers
from flask import json
from superdesk.apps.vocabularies.command import VocabulariesPopulateCommand


readonly_fields = ['display_name', 'password', 'phone', 'first_name', 'last_name']


def before_all(context):
    tests.setup(context)
    os.environ['BEHAVE_TESTING'] = '1'


def before_scenario(context, scenario):
    config = {}
    if scenario.status != 'skipped' and 'notesting' in scenario.tags:
        config['SUPERDESK_TESTING'] = False

    tests.setup(context, config)
    context.headers = [
        ('Content-Type', 'application/json'),
        ('Origin', 'localhost')
    ]
    if scenario.status != 'skipped' and 'auth' in scenario.tags:
        tests.setup_auth_user(context)

    if scenario.status != 'skipped' and 'provider' in scenario.tags:
        setup_providers(context)

    if scenario.status != 'skipped' and 'vocabulary' in scenario.tags:
        with context.app.app_context():
            cmd = VocabulariesPopulateCommand()
            filename = os.path.join(os.path.abspath(os.path.dirname("features/steps/fixtures/")), "vocabularies.json")
            cmd.run(filename)

    if scenario.status != 'skipped' and 'notification' in scenario.tags:
        tests.setup_notification(context)


def after_scenario(context, scenario):
    if 'provider' in scenario.tags:
        teardown_providers(context)

    if 'notification' in scenario.tags:
        tests.teardown_notification(context)
