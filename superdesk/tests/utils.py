from bson import ObjectId

from superdesk.core import get_current_async_app
from superdesk import get_resource_service

# TODO-ASYNC: Enable Pydantic based async services - failing ATM for some tests (investigate why)


async def find_one(resource: str, **kwargs) -> dict | None:
    async_app = get_current_async_app()

    # try:
    #     model_instance = await async_app.resources.get_resource_service(resource).find_one(**kwargs)
    #     return model_instance.to_dict(context={"use_objectid": True}) if model_instance else None
    # except KeyError:
    service = get_resource_service(resource)
    if hasattr(service, "find_one_async"):
        return await service.find_one_async(req=None, **kwargs)
    else:
        return service.find_one(req=None, **kwargs)


async def post_items(resource: str, items: list[dict]) -> None:
    # async_app = get_current_async_app()
    #
    # try:
    #     await async_app.resources.get_resource_service(resource).create(items)
    # except KeyError:
    service = get_resource_service(resource)
    if hasattr(service, "post_async"):
        return await service.post_async(items)
    else:
        return service.post(items)


async def patch_item(resource: str, item_id: str | ObjectId, updates: dict) -> None:
    # async_app = get_current_async_app()
    #
    # try:
    #     await async_app.resources.get_resource_service(resource).update(item_id, updates)
    # except KeyError:
    service = get_resource_service(resource)
    if hasattr(service, "patch_async"):
        return await service.patch_async(item_id, updates)
    else:
        return service.patch(item_id, updates)


async def system_update(resource: str, item_id: str | ObjectId, updates: dict, original: dict) -> None:
    # async_app = get_current_async_app()
    #
    # try:
    #     await async_app.resources.get_resource_service(resource).system_update(item_id, updates)
    # except KeyError:
    service = get_resource_service(resource)
    if hasattr(service, "system_update_async"):
        return await service.system_update_async(item_id, updates, original)
    else:
        return service.system_update(item_id, updates, original)


async def delete_items(resource: str, lookup: dict | None = None) -> None:
    if lookup is None:
        lookup = {}
    # async_app = get_current_async_app()
    #
    # try:
    #     await async_app.resources.get_resource_service(resource).delete_many(lookup)
    # except KeyError:
    service = get_resource_service(resource)
    if hasattr(service, "delete_action_async"):
        return await service.delete_action_async(lookup)
    else:
        return service.delete_action(lookup)
