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


def get_lock_id(*args):
    """Get id for task using all given args."""
    return "-".join((str(x) for x in args))


def get_host_id(task):
    """Get host id for given task.

    It should be unique on process level.

    :param task: celery task
    """
    return "%s:%s" % (task.request.hostname, os.getpid())
