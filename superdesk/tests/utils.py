from typing import Any
from bson import ObjectId

from superdesk.core import get_current_async_app, get_current_app
from superdesk.core.resources import ResourceModel
from superdesk import get_resource_service


def _get_eve_service(resource: str) -> Any | None:
    try:
        return get_resource_service(resource)
    except KeyError:
        return None


async def find_one(resource: str, use_eve: bool = True, **kwargs) -> dict | None:
    async_app = get_current_async_app()
    eve_service = _get_eve_service(resource)

    try:
        if not eve_service or not use_eve:
            model_instance = await async_app.resources.get_resource_service(resource).find_one(**kwargs)
            return model_instance.to_dict(context={"use_objectid": True}) if model_instance else None
    except KeyError:
        pass

    if not eve_service:
        raise RuntimeError(f"Resource {resource} not found")
    elif hasattr(eve_service, "find_one_async"):
        return await eve_service.find_one_async(req=None, **kwargs)
    else:
        return eve_service.find_one(req=None, **kwargs)


async def find_by_id(resource: str, item_id: str | ObjectId, use_eve: bool = True, **kwargs) -> dict | None:
    async_app = get_current_async_app()
    eve_service = _get_eve_service(resource)

    try:
        if not eve_service or not use_eve:
            model_instance = await async_app.resources.get_resource_service(resource).find_by_id(item_id, **kwargs)
            return model_instance.to_dict(context={"use_objectid": True}) if model_instance else None
    except KeyError:
        pass

    if not eve_service:
        raise RuntimeError(f"Resource {resource} not found")
    elif hasattr(eve_service, "find_one_async"):
        return await eve_service.find_one_async(req=None, _id=item_id, **kwargs)
    else:
        return eve_service.find_one(req=None, _id=item_id, **kwargs)


async def find_many(resource: str, lookup: dict | None = None, use_eve: bool = True, **kwargs) -> list[dict]:
    async_app = get_current_async_app()
    eve_service = _get_eve_service(resource)

    try:
        if not eve_service or not use_eve:
            cursor = await async_app.resources.get_resource_service(resource).search(lookup or {}, **kwargs)
            return await cursor.to_list_raw()
    except KeyError:
        pass

    if not eve_service:
        raise RuntimeError(f"Resource {resource} not found")
    elif hasattr(eve_service, "find_one_async"):
        return await (await eve_service.get_async(req=None, lookup=lookup, **kwargs)).to_list()
    else:
        return list(eve_service.get(req=None, lookup=lookup, **kwargs))


async def post_items(
    resource: str, items: list[dict] | list[ResourceModel], use_eve: bool = True
) -> list[str | ObjectId]:
    if not len(items):
        return []

    async_app = get_current_async_app()
    eve_service = _get_eve_service(resource)
    if isinstance(items[0], ResourceModel):
        use_eve = False

    try:
        if not eve_service or not use_eve:
            new_items = await async_app.resources.get_resource_service(resource).create(items)
            return [item.id for item in new_items]
    except KeyError:
        pass

    current_app = get_current_app()
    for item in items:
        current_app.data.mongo._mongotize(item, resource)

    if not eve_service:
        raise RuntimeError(f"Resource {resource} not found")
    elif hasattr(eve_service, "post_async"):
        return await eve_service.post_async(items)
    else:
        return eve_service.post(items)


async def patch_item(resource: str, item_id: str | ObjectId, updates: dict, use_eve: bool = True) -> None:
    async_app = get_current_async_app()
    eve_service = _get_eve_service(resource)

    try:
        if not eve_service or not use_eve:
            await async_app.resources.get_resource_service(resource).update(item_id, updates)
            return
    except KeyError:
        pass

    if not eve_service:
        raise RuntimeError(f"Resource {resource} not found")
    elif hasattr(eve_service, "patch_async"):
        await eve_service.patch_async(item_id, updates)
    else:
        return eve_service.patch(item_id, updates)


async def system_update(resource: str, item_id: str | ObjectId, updates: dict, original: dict, use_eve=True) -> None:
    async_app = get_current_async_app()
    eve_service = _get_eve_service(resource)

    try:
        if not eve_service or not use_eve:
            await async_app.resources.get_resource_service(resource).system_update(item_id, updates)
            return
    except KeyError:
        pass

    if not eve_service:
        raise RuntimeError(f"Resource {resource} not found")
    elif hasattr(eve_service, "system_update_async"):
        await eve_service.system_update_async(item_id, updates, original)
    else:
        return eve_service.system_update(item_id, updates, original)


async def delete_items(resource: str, lookup: dict | None = None, use_eve: bool = True) -> None:
    if lookup is None:
        lookup = {}
    async_app = get_current_async_app()
    eve_service = _get_eve_service(resource)

    try:
        if not eve_service or not use_eve:
            await async_app.resources.get_resource_service(resource).delete_many(lookup)
            return
    except KeyError:
        pass

    if not eve_service:
        raise RuntimeError(f"Resource {resource} not found")
    elif hasattr(eve_service, "delete_action_async"):
        await eve_service.delete_action_async(lookup)
    else:
        return eve_service.delete_action(lookup)
