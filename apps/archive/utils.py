# This file is part of Superdesk.
#
# Copyright 2013, 2025 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


from superdesk import get_resource_service
from superdesk.core.app import get_app_config, get_current_app
from superdesk.metadata.item import ASSOCIATIONS
from superdesk.privilege import GLOBAL_SEARCH_PRIVILEGE
from superdesk.users.services import current_user_has_privilege


def private_content_filter(req=None):
    """Filter out other users private content if this is a user request.

    As private we treat items where user is creator, last version creator,
    or has the item assigned to him atm.

    Also filter out content of stages not visible to current user (if any).
    """
    user = get_current_app().get_current_user_dict()
    query = {
        "bool": {
            "must": [
                {"exists": {"field": "task.desk"}},
            ],
            "must_not": [
                {"term": {"state": "draft"}},
            ],
        },
    }

    if user:
        private_filter = {
            "should": [
                # assigned to me or created by me
                {"term": {"task.user": str(user["_id"])}},
                {"term": {"version_creator": str(user["_id"])}},
                {"term": {"original_creator": str(user["_id"])}},
            ],
            "minimum_should_match": 1,
        }

        if "invisible_stages" in user:
            stages = user.get("invisible_stages")
        else:
            # TODO-ASYNC[users]: Upgrade to async when updating this module
            stages = get_resource_service("users").get_invisible_stages_ids(user.get("_id"))

        if stages:
            private_filter["must_not"] = [{"terms": {"task.stage": stages}}]

        # user can see all public content
        # as long as it's not drafts
        if current_user_has_privilege(GLOBAL_SEARCH_PRIVILEGE):
            private_filter["should"].append(
                {
                    "bool": {
                        "must": {"exists": {"field": "task.desk"}},
                        "must_not": {"term": {"state": "draft"}},
                    }
                }
            )

        # if user has no global search access, only show him content on his desks
        # and not on any desk
        else:
            # TODO-ASYNC[vocabularies]: Convert ``get_by_user`` to async when upgrading this module
            desks = get_resource_service("user_desks").get_by_user(user["_id"]) or []
            private_filter["should"].append(
                {"terms": {"task.desk": [str(d["_id"]) for d in desks]}},
            )

        query = {
            "bool": {
                "should": [
                    {"bool": private_filter},
                    {"bool": {"must_not": {"term": {"state": "draft"}}}},
                ],
                "minimum_should_match": 1,
            },
        }

    if req is not None and req.args is not None and req.args.get("scope"):
        query["bool"].setdefault("must", []).append({"term": {"scope": req.args.get("scope")}})
    else:
        query["bool"].setdefault("must_not", []).append({"exists": {"field": "scope"}})
    return query


def flush_renditions(updates, original):
    """Removes incorrect custom renditions from `updates`.

    Sometimes, when image (association) in `updates` is small, it can't fill all custom renditions,
    in this case, after merge of `updates` and `original`, custom renditions will point to old values from `original`,
    which is wrong.
    This function finds such cases and removes them.

    :param dict updates: updates for the document
    :param original: original is document
    """
    if ASSOCIATIONS not in original or ASSOCIATIONS not in updates or not updates[ASSOCIATIONS]:
        return

    default_renditions = ("original", "baseImage", "thumbnail", "viewImage")

    for key in [k for k in updates[ASSOCIATIONS] if k in original[ASSOCIATIONS]]:
        try:
            new_href = updates[ASSOCIATIONS][key]["renditions"]["original"]["href"]
            old_href = original[ASSOCIATIONS][key]["renditions"]["original"]["href"]
        except (KeyError, TypeError):
            continue
        else:
            if new_href != old_href:
                new_renditions = [r for r in updates[ASSOCIATIONS][key]["renditions"] if r not in default_renditions]
                old_renditions = [r for r in original[ASSOCIATIONS][key]["renditions"] if r not in default_renditions]
                for old_rendition in old_renditions:
                    if old_rendition not in new_renditions:
                        updates[ASSOCIATIONS][key]["renditions"][old_rendition] = None


def remove_is_queued(item):
    if get_app_config("PUBLISH_ASSOCIATED_ITEMS"):
        associations = item.get("associations") or {}
        for associations_key, associated_item in associations.items():
            if not associated_item:
                continue
            if associated_item.get("is_queued"):
                associated_item["is_queued"] = None
