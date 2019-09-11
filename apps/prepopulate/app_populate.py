# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import json
import os
import superdesk
import logging

from superdesk import get_resource_service


logger = logging.getLogger(__name__)


def populate_table_json(service_name, json_data):
    service = get_resource_service(service_name)
    for item in json_data:
        id_name = item.get("_id")

        if service.find_one(_id=id_name, req=None):
            service.put(id_name, item)
        else:
            service.post([item])


def process_file(filepath):
    """Insert or update the data from file.

    Filename is used to determine a collection.
    The format of the file used is JSON.
    :param filepath: absolute filepath
    :return: nothing
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError

    [table_name, ext] = os.path.basename(filepath).split('.')

    with open(filepath, 'rt') as vocabularies:
        json_data = json.loads(vocabularies.read())
        populate_table_json(table_name, json_data)


class AppPopulateCommand(superdesk.Command):
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

    option_list = (
        superdesk.Option('--filepath', '-f', dest='filepath', required=True),
    )

    def run(self, filepath):
        process_file(filepath)


superdesk.command('app:populate', AppPopulateCommand())
