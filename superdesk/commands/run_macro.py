# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import click

from superdesk.core import json
from superdesk import get_resource_service

from .async_cli import cli


@cli.command("app:run_macro")
@click.option("--name", "-n", "macro_name", required=True, type=str, help="Name of the macro to run.")
@click.option("--kwargs", "-k", "kwargs", type=str, help="Keyword arguments to pass to the macro.")
async def run_macro(macro_name, kwargs):
    """Executes a macro by given name and optional keyword arguments.

    Example:
    ::

        $ app:run_macro --name clean_keywords --kwargs {"repo":"archived"}

    """
    kwargs = json.loads(kwargs)
    macro = get_resource_service("macros").get_macro_by_name(macro_name)

    if not macro:
        print("Failed to locate macro {}.".format(macro_name))
        return

    await macro["callback"](**kwargs)
