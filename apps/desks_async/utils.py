from bson import ObjectId
from superdesk.types import DesksResourceModel


async def get_desk_name_by_id(desk_id: ObjectId) -> str | None:
    desk = await DesksResourceModel.get_service().find_by_id_raw(desk_id)
    return desk.get("name") if desk else None
