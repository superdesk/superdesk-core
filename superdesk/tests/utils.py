from bson import ObjectId

from superdesk.core import get_current_async_app
from superdesk.core.resources import ResourceModel
from superdesk import get_resource_service


async def find_one(resource: str, **kwargs) -> dict | None:
    async_app = get_current_async_app()

    try:
        model_instance = await async_app.resources.get_resource_service(resource).find_one(**kwargs)
        return model_instance.to_dict(context={"use_objectid": True}) if model_instance else None
    except KeyError:
        pass

    service = get_resource_service(resource)
    if hasattr(service, "find_one_async"):
        return await service.find_one_async(req=None, **kwargs)
    else:
        return service.find_one(req=None, **kwargs)


async def find_by_id(resource: str, item_id: str | ObjectId, **kwargs) -> dict | None:
    async_app = get_current_async_app()

    try:
        model_instance = await async_app.resources.get_resource_service(resource).find_by_id(**kwargs)
        return model_instance.to_dict(context={"use_objectid": True}) if model_instance else None
    except KeyError:
        pass

    service = get_resource_service(resource)
    if hasattr(service, "find_one_async"):
        return await service.find_one_async(req=None, _id=item_id, **kwargs)
    else:
        return service.find_one(req=None, _id=item_id, **kwargs)


async def find_many(resource: str, lookup: dict | None = None, **kwargs) -> list[dict]:
    async_app = get_current_async_app()

    try:
        cursor = await async_app.resources.get_resource_service(resource).search(lookup or {}, **kwargs)
        return await cursor.to_list_raw()
    except KeyError:
        pass

    service = get_resource_service(resource)
    if hasattr(service, "find_one_async"):
        return await (await service.get_async(req=None, lookup=lookup, **kwargs)).to_list()
    else:
        return list(service.get(req=None, lookup=lookup, **kwargs))


async def post_items(
    resource: str, items: list[dict] | list[ResourceModel], use_eve: bool = False
) -> list[str | ObjectId]:
    async_app = get_current_async_app()

    try:
        eve_service = get_resource_service(resource)
    except KeyError:
        eve_service = None

    try:
        if eve_service is None or not use_eve:
            new_items = await async_app.resources.get_resource_service(resource).create(items)
            return [item.id for item in new_items]
    except KeyError:
        pass

    if hasattr(eve_service, "post_async"):
        return await eve_service.post_async(items)
    else:
        return eve_service.post(items)


async def patch_item(resource: str, item_id: str | ObjectId, updates: dict) -> None:
    async_app = get_current_async_app()

    try:
        await async_app.resources.get_resource_service(resource).update(item_id, updates)
        return
    except KeyError:
        pass

    service = get_resource_service(resource)
    if hasattr(service, "patch_async"):
        await service.patch_async(item_id, updates)
    else:
        return service.patch(item_id, updates)


async def system_update(resource: str, item_id: str | ObjectId, updates: dict, original: dict) -> None:
    async_app = get_current_async_app()

    try:
        await async_app.resources.get_resource_service(resource).system_update(item_id, updates)
        return
    except KeyError:
        pass

    service = get_resource_service(resource)
    if hasattr(service, "system_update_async"):
        await service.system_update_async(item_id, updates, original)
    else:
        return service.system_update(item_id, updates, original)


async def delete_items(resource: str, lookup: dict | None = None) -> None:
    if lookup is None:
        lookup = {}
    async_app = get_current_async_app()

    try:
        await async_app.resources.get_resource_service(resource).delete_many(lookup)
        return
    except KeyError:
        pass

    service = get_resource_service(resource)
    if hasattr(service, "delete_action_async"):
        await service.delete_action_async(lookup)
    else:
        return service.delete_action(lookup)
