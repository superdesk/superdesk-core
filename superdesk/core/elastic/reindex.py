# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2024 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from typing import Optional, Dict, Any
from time import sleep

from elasticsearch.exceptions import NotFoundError
from click import progressbar

from .utils import generate_index_name
from .sync_client import ElasticResourceClient


def reindex(client: ElasticResourceClient, mapping: Dict[str, Any], requests_per_second: int = 1000):
    alias = client.config.index
    old_index = None
    try:
        indexes = client.elastic.indices.get_alias(name=alias)
        for index, aliases in indexes.items():
            old_index = index
            specs = aliases["aliases"][alias]
            if specs and specs["is_write_index"]:
                break
    except NotFoundError:
        pass

    if old_index:
        print(f"OLD INDEX {old_index}")

    # Create new index
    new_index = generate_index_name(alias)
    client.elastic.indices.create(
        index=new_index,
        body={} if not client.config.settings else client.config.settings,
    )
    client.elastic.indices.put_mapping(index=new_index, body=mapping)

    print(f"NEW INDEX {new_index}")

    if not old_index:
        try:
            client.elastic.indices.get(index=alias)
            print("Old index is not using an alias")
            _background_reindex(client, alias, new_index, requests_per_second=requests_per_second, refresh=True)
            client.elastic.indices.update_aliases(
                body={
                    "actions": [
                        {
                            "add": {
                                "index": new_index,
                                "alias": alias,
                                "is_write_index": True,
                            },
                        },
                        {
                            "remove_index": {
                                "index": alias,
                            },
                        },
                    ],
                }
            )
        except NotFoundError:
            print("There is no index to reindex from, done.")
            client.elastic.indices.put_alias(index=new_index, name=alias)
        return

    # tmp index will be used for new items arriving during reindex
    tmp_index = f"{old_index}-tmp"
    client.elastic.indices.create(
        index=tmp_index,
        body={} if not client.config.settings else client.config.settings,
    )
    client.elastic.indices.put_mapping(index=tmp_index, body=mapping)
    print(f"TMP INDEX {tmp_index}")

    # add tmp index as writable
    client.elastic.indices.update_aliases(
        body={
            "actions": [
                {
                    "add": {  # add tmp index as write index
                        "index": tmp_index,
                        "alias": alias,
                        "is_write_index": True,
                    },
                },
                {
                    "add": {  # make sure the old index is not write index
                        "index": old_index,
                        "alias": alias,
                        "is_write_index": False,
                    },
                },
            ],
        }
    )
    _background_reindex(client, old_index, new_index, requests_per_second=requests_per_second)

    # add new index if writable, tmp readonly
    client.elastic.indices.update_aliases(
        body={
            "actions": [
                {
                    "add": {  # add new index as write index
                        "index": new_index,
                        "alias": alias,
                        "is_write_index": True,
                    },
                },
                {
                    "add": {  # make tmp index readonly
                        "index": tmp_index,
                        "alias": alias,
                        "is_write_index": False,
                    },
                },
                {
                    "remove_index": {
                        "index": old_index,
                    },
                },
            ],
        }
    )

    # do it as fast as possible
    _background_reindex(client, tmp_index, new_index, refresh=True)

    print(f"REMOVE TMP INDEX {tmp_index}")
    client.elastic.indices.delete(index=tmp_index)


def _background_reindex(
    client: ElasticResourceClient,
    old_index: str,
    new_index: str,
    *,
    requests_per_second: Optional[int] = None,
    refresh: bool = False,
):
    resp = client.elastic.reindex(
        body={
            "source": {"index": old_index},
            "dest": {"index": new_index, "version_type": "external"},
        },
        requests_per_second=requests_per_second,
        wait_for_completion=False,
        refresh=refresh,
    )
    task_id = resp["task"]
    print(f"REINDEXING {old_index} to {new_index} (task {task_id})")

    # first get total number of items
    while True:
        sleep(1.0)
        try:
            task = client.elastic.tasks.get(task_id=task_id)
        except NotFoundError:
            print("Task not found, reindexing done.")
            return
        if task["completed"]:
            print_task_done(task)
            return
        elif task["task"]["status"]["total"]:
            break

    # now it can render progress
    last_created = 0
    with progressbar(length=task["task"]["status"]["total"], label="Reindexing") as bar:
        while True:
            sleep(2.0)
            try:
                task = client.elastic.tasks.get(task_id=task_id)
            except NotFoundError:
                print("Task not found, reindexing done.")
                return
            if task["task"]["status"]["created"] and task["task"]["status"]["created"] > last_created:
                bar.update(task["task"]["status"]["created"] - last_created)
                last_created = task["task"]["status"]["created"]
            if task["completed"]:
                bar.finish()
                break

    print_task_done(task)


def print_task_done(task):
    took = int(task["response"]["took"] / 1000)
    print(f"DONE in {took}s")
