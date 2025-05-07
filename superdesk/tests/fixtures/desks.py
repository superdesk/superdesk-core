from bson import ObjectId
from superdesk.types import DesksResourceModel


SPORTS_DESK_ID = ObjectId()
# FINANCE_DESK_ID = ObjectId()


def sports_desk() -> DesksResourceModel:
    return DesksResourceModel(
        id=SPORTS_DESK_ID,
        name="Sports",
    )


# def finance_desk() -> DesksResourceModel:
#     return DesksResourceModel(
#         id=FINANCE_DESK_ID,
#         name="Finance",
#     )


def all_desks() -> list[DesksResourceModel]:
    # return [sports_desk(), finance_desk()]
    return [sports_desk()]
