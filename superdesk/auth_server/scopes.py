# This file is part of Superdesk.
#
# Copyright 2019 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

"""Scopes allowed in auth_server"""

from enum import Enum

# please refer to /docs/auth_server.rst for details on scopes

Scope = Enum('Scope', [
    'ARCHIVE_READ',
    'DESKS_READ',
    'PLANNING_READ',
    'CONTACTS_READ',
    'USERS_READ',
    'ASSIGNMENTS_READ',
    'EVENTS_READ'
])


allowed_scopes = {s.name for s in Scope}
