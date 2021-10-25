# -*- coding: utf-8; -*-
# This file is part of Superdesk.
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license
#
# Author  : tomas
# Creation: 2018-11-14 15:37

from superdesk.commands.data_updates import BaseDataUpdate


def get_root_nodes(tree_items):
    root_nodes = []

    for key in tree_items:
        node = tree_items[key]
        if node.parent is None:
            root_nodes.append(node)

    return root_nodes


def get_ids_recursive(list_of_nodes):
    ids = []

    for node in list_of_nodes:
        if len(node.children) > 0:
            ids.extend(get_ids_recursive(node.children))

        ids.append(node.id)

    return ids


class TreeNode:
    def __init__(self, id):
        self.id = id
        self.parent = None
        self.children = []


class DataUpdate(BaseDataUpdate):

    resource = "archive"

    def forwards(self, mongodb_collection, mongodb_database):

        # building multiple trees
        tree_items = {}
        for item in mongodb_collection.find({"translated_from": {"$exists": True}}):
            node_id = item["_id"]

            if node_id not in tree_items:
                tree_items[node_id] = TreeNode(node_id)

            node = tree_items[node_id]

            parent_id = item["translated_from"]

            if parent_id not in tree_items:
                tree_items[parent_id] = TreeNode(parent_id)

            node.parent = tree_items[parent_id]
            node.parent.children.append(node)

        # processing trees
        for root_node in get_root_nodes(tree_items):
            ids = get_ids_recursive([root_node])

            print(mongodb_collection.update_many({"_id": {"$in": ids}}, {"$set": {"translation_id": root_node.id}}))

    def backwards(self, mongodb_collection, mongodb_database):
        raise NotImplementedError()
