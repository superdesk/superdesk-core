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
import logging
import json
import click

from superdesk import get_resource_service
from superdesk.commands import cli


logger = logging.getLogger(__name__)


@cli.command("app:populate")
@click.option("--filepath", "-f", required=True)
async def cli_app_populate(filepath):
    """
    Insert or update data in collection using sample file.

    Specified file must be a valid json file.
    Filename will be used as a collection name where data will be inserted or updated.
    If document already exists in the collection, it will be updated.

    Example:
    ::

        $ python manage.py app:populate --filepath=data/content_types.json
        $ python manage.py app:populate --filepath=data/planning_types.json
        $ python manage.py app:populate --filepath=data/vocabularies.json

    """

    await AppPopulateCommand().run(filepath)


async def populate_table_json(service_name, json_data):
    service = get_resource_service(service_name)
    for item in json_data:
        id_name = item.get("_id")

        if hasattr(service, "find_one_async"):
            # This is an async resource service, use async methods
            if id_name and await service.find_one_async(_id=id_name, req=None):
                await service.put_async(id_name, item)
            else:
                await service.post_async([item])
        else:
            if id_name and service.find_one(_id=id_name, req=None):
                service.put(id_name, item)
            else:
                service.post([item])


async def process_file(filepath):
    """Insert or update the data from file.

    Filename is used to determine a collection.
    The format of the file used is JSON.
    :param filepath: absolute filepath
    :return: nothing
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError

    [table_name, ext] = os.path.basename(filepath).split(".")

    with open(filepath, "rt") as vocabularies:
        json_data = json.loads(vocabularies.read())
        await populate_table_json(table_name, json_data)


class AppPopulateCommand:
    async def run(self, filepath):
        await process_file(filepath)
