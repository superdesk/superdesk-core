from superdesk import get_resource_service


async def set_valid_content_profile(item, **kwargs):
    content_profile = await get_resource_service("content_types").find_one_async(req=None, _id="bar")
    item["profile"] = content_profile.get("_id")

    return item


name = "set_valid_profile_id"
label = "Set valid content profile"
callback = set_valid_content_profile
access_type = "backend"
action_type = "direct"
