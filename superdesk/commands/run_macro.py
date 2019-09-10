# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license
import superdesk
import json


class RunMacro(superdesk.Command):
    r"""Executes a macro by given name and optional keyword arguments.

    Example:
    ::

        $ app:run_macro --name clean_keywords --kwargs {"repo":"archived"}

    """

    option_list = [
        superdesk.Option('--name', '-n', dest='macro_name', required=True),
        superdesk.Option('--kwargs', '-k', dest='kwargs', required=False)
    ]

    def run(self, macro_name, kwargs):
        kwargs = json.loads(kwargs)
        macro = superdesk.get_resource_service('macros').get_macro_by_name(macro_name)

        if not macro:
            print('Failed to locate macro {}.'.format(macro_name))
            return

        macro['callback'](**kwargs)


superdesk.command('app:run_macro', RunMacro())
