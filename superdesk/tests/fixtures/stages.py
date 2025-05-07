from bson import ObjectId

# from .desks import SPORTS_DESK_ID, FINANCE_DESK_ID
from .desks import SPORTS_DESK_ID


SPORTS_WORKING_STAGE_ID = ObjectId()
# FINANCE_WORKING_STAGE_ID = ObjectId()


def sports_working_stage() -> dict:
    return {
        "_id": SPORTS_WORKING_STAGE_ID,
        "name": "working stage",
        "desk": SPORTS_DESK_ID,
    }


# def finance_working_stage() -> dict:
#     return {
#         "_id": FINANCE_WORKING_STAGE_ID,
#         "name": "working stage",
#         "desk": FINANCE_DESK_ID,
#     }


def all_stages() -> list[dict]:
    # return [sports_working_stage(), finance_working_stage()]
    return [sports_working_stage()]
