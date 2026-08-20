# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2026 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import logging

from superdesk.core.app import SuperdeskAsyncApp
from superdesk.core.module import Module

from .config import get_bot_token, get_signing_secret
from .resources import slack_user_links_config
from .views import slack_endpoints

# Imported so Celery registers the tasks when the module is loaded
from . import tasks  # noqa: F401

# Imported so the CLI commands are registered when the module is loaded
from . import commands  # noqa: F401


logger = logging.getLogger(__name__)


def init_slack(app: SuperdeskAsyncApp) -> None:
    if get_signing_secret() and get_bot_token():
        logger.info("Slack module is configured")
    else:
        logger.info("Slack module is inactive, set SLACK_SIGNING_SECRET and SLACK_BOT_TOKEN to enable it")


module = Module(
    name="superdesk.slack",
    init=init_slack,
    resources=[slack_user_links_config],
    endpoints=[slack_endpoints],
)
