from bson import ObjectId
from superdesk.types import DesksResourceModel


SPORTS_DESK_ID = ObjectId()


def sports_desk() -> DesksResourceModel:
    return DesksResourceModel(
        id=SPORTS_DESK_ID,
        name="sports",
    )


def all_desks() -> list[DesksResourceModel]:
    return [sports_desk()]
