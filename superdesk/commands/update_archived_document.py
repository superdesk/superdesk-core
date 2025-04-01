# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import ast

import json
import click
import bson

from superdesk import get_resource_service
from .async_cli import cli
from .delete_archived_document import DeleteArchivedDocumentCommand


@cli.command("app:updateArchivedDocument")
@click.option("--ids", "-i", required=True)
@click.option("--field", "-f", required=True)
@click.option("--value", "-v", required=True)
@click.option("--parseNeeded", "-p", "parse_needed", is_flag=True, default=False)
def cli_update_archived_document(ids, field, value, parse_needed):
    """
    Update metadata for a document in both Mongodb and ElasticSearch by supplying ids
    field to update and the value for the update

    --field   Field name
    --value   Value to be set in the field
    --parseNeeded   Optional. True if value is a complex type, not an int or string

    Example:
    ::

        $ manage.py app:updateArchivedDocument --ids='["588c1df11d41c80928015601","588c1b901d41c805dce70df0"]'
            --field=anpa_category
            --value=[{"scheme" : null,"qcode" : "f","subject" : "04000000","name" : "Finance"}]
            --parseNeeded=True

    """

    UpdateArchivedDocumentCommand().run(ids, field, value, parse_needed)


class UpdateArchivedDocumentCommand:
    def run(self, ids, field, value, parseNeeded=False):
        ids = ast.literal_eval(ids)

        if parseNeeded:
            try:
                value = json.loads(value)
            except Exception as e:
                print("Error in parsing the value: {}".format(value))
                print(e)
                return

        if ids and len(ids) > 0:
            items = DeleteArchivedDocumentCommand().get_archived_items(ids)

            for item in items:
                get_resource_service("archived").system_update(bson.ObjectId(item["_id"]), {field: value}, item)
                print("Archived item {} has been updated.".format(item["_id"]))
                print("-" * 45)
