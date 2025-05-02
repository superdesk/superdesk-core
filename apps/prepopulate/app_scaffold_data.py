# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import logging

import click

from superdesk.resource_fields import ID_FIELD, VERSION
from superdesk import get_resource_service
from superdesk.commands import cli
from apps.archive.archive import SOURCE as ARCHIVE
from apps.archive.common import generate_unique_id_and_name, remove_unwanted, insert_into_versions_async
from superdesk.metadata.item import GUID_TAG, FAMILY_ID, ITEM_STATE, CONTENT_STATE
from superdesk.metadata.utils import generate_guid

logger = logging.getLogger(__name__)


@cli.command("app:scaffold_data")
@click.option("--no-of-stories", "-n", "no_of_stories", default=200, type=int)
async def scaffold_data_command(no_of_stories) -> int:
    return await scaffold_data(no_of_stories)


async def scaffold_data(no_of_stories: int) -> int:
    logger.info("Starting scaffolding")
    no_of_stories = int(no_of_stories)

    desks = get_resource_service("desks").get(None, {})

    for i, desk in enumerate(desks):
        logger.info("Adding items for desk:" + str(desk["_id"]))
        await ingest_items_for(desk, no_of_stories, i + 1)
    return 0


async def ingest_items_for(desk, no_of_stories, skip_index):
    desk_id = desk["_id"]
    stage_id = desk["incoming_stage"]

    bucket_size = min(100, no_of_stories)

    no_of_buckets = len(range(0, no_of_stories, bucket_size))

    for x in range(0, no_of_buckets):
        skip = x * bucket_size * skip_index
        logger.info("Page : {}, skip: {}".format(x + 1, skip))
        cursor = await get_resource_service("published").get_from_mongo_async(None, {})
        num_items = await cursor.count()
        logger.info("Inserting {} items".format(num_items))
        archive_items = []

        async for item in cursor.skip(skip).limit(bucket_size):
            dest_doc = dict(item)
            new_id = generate_guid(type=GUID_TAG)
            dest_doc[ID_FIELD] = new_id
            dest_doc["guid"] = new_id
            generate_unique_id_and_name(dest_doc)

            dest_doc[VERSION] = 1
            dest_doc[ITEM_STATE] = CONTENT_STATE.FETCHED
            user_id = desk.get("members", [{"user": None}])[0].get("user")
            dest_doc["original_creator"] = user_id
            dest_doc["version_creator"] = user_id

            from apps.tasks import send_to

            await send_to(dest_doc, desk_id=desk_id, stage_id=stage_id, user_id=user_id)
            dest_doc[VERSION] = 1  # Above step increments the version and needs to reset
            dest_doc[FAMILY_ID] = item["_id"]

            remove_unwanted(dest_doc)
            archive_items.append(dest_doc)

        await get_resource_service(ARCHIVE).post_async(archive_items)
        for item in archive_items:
            await insert_into_versions_async(id_=item[ID_FIELD])
