from superdesk import get_resource_service
from superdesk.resource_fields import ID_FIELD, GUID_FIELD

from content_api.items.model import ContentAPIItem, PubStatusType
from content_api.items.async_service import ContentAPIItemService


async def publish_docs_to_content_api(docs: list[dict]) -> list[str]:
    ids = []
    for doc in docs:
        item_id = doc.pop(GUID_FIELD)
        doc[ID_FIELD] = item_id
        ids.append(await publish_doc_to_content_api(doc))
    return ids


async def publish_doc_to_content_api(item_dict: dict) -> str:
    item = ContentAPIItem.from_dict(item_dict)
    service = ContentAPIItemService()

    original = await service.find_by_id(item.id)
    if original:
        item.subscribers = list(set(original.subscribers or []) | set(item.subscribers or []))

    process_associations(item, original)
    create_version_doc(item)

    if original:
        await service.update(original.id, item.to_dict(context={"use_objectid": True}))
        return original.id
    else:
        return (await service.create([item]))[0]


def process_associations(updates: ContentAPIItem, original: ContentAPIItem | None) -> None:
    """Update associations using existing published item and ensure that associated item subscribers
    are equal or subset of the parent subscribers.
    :param updates:
    :param original:
    :return:
    """

    subscribers = updates.subscribers or []
    for assoc, update_assoc in (updates.associations or {}).items():
        if not update_assoc:
            continue

        if original:
            original_assoc = (original.associations or {}).get(assoc)

            if original_assoc:
                if original_assoc.get(ID_FIELD) == update_assoc.get(ID_FIELD):
                    update_assoc["subscribers"] = list(
                        set(original_assoc.get("subscribers") or []) | set(update_assoc.get("subscribers") or [])
                    )

                if original_assoc.get("renditions"):
                    update_assoc.setdefault("renditions", {})
                    for rend in original_assoc["renditions"]:
                        update_assoc["renditions"].setdefault(rend, None)

        update_assoc["subscribers"] = list(set(update_assoc["subscribers"]) & set(subscribers))

    # remove associations which were there previously
    # but are missing now
    if original and original.associations:
        if not updates.associations:
            updates.associations = {}
        for assoc in original.associations:
            updates.associations.setdefault(assoc, None)

    # If there are no associations anymore, then set the entire associations field to None
    if updates.associations is not None and not any([assoc for assoc in updates.associations.values()]):
        updates.associations = None


# TODO-ASYNC: Use new versioning system
def create_version_doc(item: ContentAPIItem) -> None:
    """
    Store the item in the item version collection
    :param item:
    :return:
    """
    version_item = item.to_dict(context={"use_objectid": True})
    version_item["_id_document"] = version_item.pop("_id")
    get_resource_service("items_versions").create([version_item])
    # if the update is a cancel we need to cancel all versions
    if item.pubstatus == PubStatusType.CANCELLED:
        _cancel_versions(item.id)


# TODO-ASYNC: Use new versioning system
def _cancel_versions(doc_id: str) -> None:
    """
    Given an id of a document set the pubstatus to canceled for all versions
    :param doc_id:
    :return:
    """
    query = {"_id_document": doc_id}
    update = {"pubstatus": "canceled"}
    for item in get_resource_service("items_versions").get_from_mongo(req=None, lookup=query):
        if item.get("pubstatus") != "canceled":
            get_resource_service("items_versions").update(item["_id"], update, item)
