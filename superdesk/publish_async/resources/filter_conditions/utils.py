import re

from superdesk.types import FilterConditionsResource

from .filter_condition_params import get_available_filter_params


async def check_similar_filter_conditions(filter_condition: dict) -> list[FilterConditionsResource]:
    """Checks for similar items

    Checks if the given filter condition already exists (for text fields like headline) or
    if there's any other filter condition that contains the given filter
    condition (for controlled vocabulary fields like urgency).
    For example: if filter_condition ['urgency' in 3,4] exists and if
    filter condition ['urgency' in 3] is searched we'll have a match

    :param filter_condition: Filter conditions to be tested
    :return: Returns the list of matching filter conditions
    """
    service = FilterConditionsResource.get_service()
    parameters = await get_available_filter_params()
    parameter = [p for p in parameters if p.field == filter_condition["field"]]
    if "in" in parameter[0].operators or "nin" in parameter[0].operators:
        # this is a controlled vocabulary field so find the overlapping values
        existing_docs = await (
            await service.search(
                {
                    "field": filter_condition["field"],
                    "operator": filter_condition["operator"],
                    "value": {"$regex": re.compile(".*{}.*".format(filter_condition["value"]), re.IGNORECASE)},
                }
            )
        ).to_list()
        parameter[0].operators.remove(filter_condition["operator"])
        existing_docs.extend(
            await (
                await service.search(
                    {
                        "field": filter_condition["field"],
                        "operator": parameter[0].operators[0],
                        "value": {"$not": re.compile(".*{}.*".format(filter_condition["value"]), re.IGNORECASE)},
                    }
                )
            ).to_list()
        )
    else:
        # find the exact matches
        existing_docs = await (
            await service.search(
                {
                    "field": filter_condition["field"],
                    "operator": filter_condition["operator"],
                    "value": {"$regex": re.compile("{}".format(filter_condition["value"]), re.IGNORECASE)},
                }
            )
        ).to_list()
    return existing_docs
