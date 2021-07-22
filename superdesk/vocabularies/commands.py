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
import logging

from superdesk import get_resource_service


logger = logging.getLogger(__name__)


def update_items(vocabularies, fields, service):
    ids = list(item.get("_id") for item in service.get_from_mongo(req=None, lookup=None))
    count = 0
    print(service, " items to be checked: ", len(ids))
    for _id in ids:
        item = service.find_one(_id=_id, req=None)
        updates = update_item(item, vocabularies, fields)
        if updates:
            print(service, " update: ", updates, " for item with id:", _id)
            service.system_update(item["_id"], updates, item)
            count = count + 1
    print(service, " updated: ", count, "/", len(ids))


def get_vocabularies(vocabularies_list):
    vocabularies = {vocabulary["_id"]: vocabulary for vocabulary in vocabularies_list}
    for vocabulary in vocabularies.values():
        for item in vocabulary.get("items", []):
            if "is_active" in item:
                del item["is_active"]
            item["scheme"] = vocabulary["_id"]
        unique_name = vocabulary.get("unique_field", "qcode")
        vocabulary["values"] = {item[unique_name]: item for item in vocabulary.get("items", [])}
    return vocabularies


def is_changed(old, new):
    if len(old) != len(new):
        return True

    for value in old:
        if value == "translations":
            continue
        if value not in new or old[value] != new[value]:
            return True
    if old.get("name", None) != new.get("name", None):
        return True

    old_translations = old.get("translations", {})
    new_translations = new.get("translations", {})

    if len(old_translations) != len(new_translations):
        return True

    for field in old_translations:
        old_field_translations = old_translations.get(field, {})
        new_field_translations = new_translations.get(field, {})

        if len(old_field_translations) != len(new_field_translations):
            return True

        for language in old_field_translations:
            if old_field_translations[language] != new_field_translations.get(language, None):
                return True
    return False


def update_item(item, vocabularies, fields):
    updates = {}
    for field in fields:
        for value in item.get(field, []):
            scheme = value.get("scheme", None)
            qcode = value.get("qcode", None)
            if qcode and scheme and scheme in vocabularies:
                new_value = vocabularies[scheme].get("values", {}).get(qcode, None)
                if not new_value:
                    continue
                if is_changed(value, new_value):
                    if field not in updates:
                        updates[field] = []
                    updates[field].append(new_value)
    return updates


class UpdateVocabulariesInItemsCommand(superdesk.Command):
    """
    Update documents in `archive` and `published` collections which contain CV related fields:
    `subject`, `genre`, `place`, `anpa_category` with corresponding data from vocabularies.

    Example:
    ::

        $ python manage.py vocabularies:update_archive

    """

    option_list = ()

    def run(self):
        fields = ["subject", "genre", "place", "anpa_category"]
        lookup = {"type": "manageable", "service": {"$exists": True}}
        vocabularies_list = get_resource_service("vocabularies").get(req=None, lookup=lookup)
        vocabularies = get_vocabularies(vocabularies_list)

        update_items(vocabularies, fields, get_resource_service("archive"))
        update_items(vocabularies, fields, get_resource_service("published"))


superdesk.command("vocabularies:update_archive", UpdateVocabulariesInItemsCommand())
