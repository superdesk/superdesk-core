from bson import ObjectId
from superdesk.types import DesksResourceModel


async def get_desk_name_by_id(desk_id: ObjectId) -> str | None:
    """
    Retrieve the name of a desk by its unique identifier.

    This function attempts to find a desk by its ID using the `DesksResourceModel`
    service. If the desk is found, its name is returned. If the desk does not exist,
    the function will return ``None``.

    :param desk_id: The unique identifier of the desk to retrieve.
    :returns: The name of the desk if found, otherwise ``None``.
    """

    desk = await DesksResourceModel.get_service().find_by_id_raw(desk_id)
    return desk.get("name") if desk else None


async def add_member_to_desk(desk_id: ObjectId, user_id: ObjectId) -> None:
    """
    Function to add a member to a desk by their user ID. This function retrieves the desk data using
    the provided desk ID, adds the user to the desk's members list, and updates the desk with the
    new members' information. The function does not return any value.

    :param desk_id: The unique identifier of the desk to which a member is to be added.
    :param user_id: The unique identifier of the user to add to the desk.
    :raises ValueError: If the desk with the specified ID is not found.
    """

    service = DesksResourceModel.get_service()
    desk = await service.find_by_id(desk_id)
    if not desk:
        raise ValueError('desk "{}" not found'.format(desk_id))
    members = desk.to_dict().get("members", [])
    members.append({"user": user_id})
    updates = {"members": members}
    await service.on_update(updates, desk)
    await service.system_update(desk.id, updates)
