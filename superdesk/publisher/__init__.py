# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

"""
Superdesk Web Pubisher specific modules.
"""

import superdesk


superdesk.privilege(name='livesite', label='Livesite Editor',
                    description='Edit a site live on Web Publisher')
