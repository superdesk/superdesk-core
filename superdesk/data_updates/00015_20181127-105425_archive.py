# -*- coding: utf-8; -*-
# This file is part of Superdesk.
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license
#
# Author  : tomas
# Creation: 2018-11-27 10:54

from superdesk.commands.data_updates import BaseDataUpdate
from superdesk import get_resource_service

# This upgrade script does the same as the previous one 00014_20181114-153727_archive.py
# except this works across multiple collections


def get_root_nodes(tree_items):
    root_nodes = []

    for key in tree_items:
        node = tree_items[key]
        if node.parent is None:
            root_nodes.append(node)

    return root_nodes


def get_ids_recursive(list_of_nodes, resource):
    # walks the tree and returns ids of items with a specified resource

    ids = []

    for node in list_of_nodes:
        if len(node.children) > 0:
            ids.extend(get_ids_recursive(node.children, resource))

        if node.resource == resource:
            ids.append(node.id)

    return ids


class TreeNode:
    def __init__(self, id):
        self.id = id
        self.parent = None
        self.resource = None
        self.children = []


class DataUpdate(BaseDataUpdate):

    resource = "archive"  # will use multiple resources, keeping this here so validation passes

    def forwards(self, mongodb_collection, mongodb_database):
        tree_items = {}

        # `translated_from` can refer to archive['_id'] or published['item_id']

        for resource in ["archive", "published"]:
            collection = mongodb_database[resource]

            # building multiple trees
            for item in collection.find({"translated_from": {"$exists": True}}):
                node_id = item["_id"]

                if node_id not in tree_items:
                    tree_items[node_id] = TreeNode(node_id)

                node = tree_items[node_id]
                node.resource = resource
                parent_id = item["translated_from"]

                if parent_id not in tree_items:
                    tree_items[parent_id] = TreeNode(parent_id)

                node.parent = tree_items[parent_id]
                node.parent.children.append(node)

        # processing trees
        for root_node in get_root_nodes(tree_items):
            updates = {"translation_id": root_node.id}

            for resource in ["archive", "published"]:
                service = get_resource_service(resource)
                ids = get_ids_recursive([root_node], resource)

                for item_id in ids:
                    item = service.find_one(req=None, _id=item_id)

                    if item is not None:
                        print(service.system_update(item_id, updates, item))

    def backwards(self, mongodb_collection, mongodb_database):
        raise NotImplementedError()
