from superdesk import get_resource_service
from superdesk.resource_fields import VERSION
from superdesk.metadata.packages import RESIDREF, GROUPS, REFS, GROUP_ID, ROOT_GROUP, ID_REF


def get_residrefs(package: dict) -> list[str]:
    """
    Fetches all residual references from the given package.

    This function is used to collect all residual references (`RESIDREF`) present
    within the nested data structure of a package dictionary. It navigates through
    the `GROUPS` key (if present) and finds all related `REFS` to extract the
    `RESIDREF` values.

    :param package: A dictionary representing a package containing possible nested groups and references.
    :return: A list of strings containing all residual references found in the package.
    """

    return [ref.get(RESIDREF) for group in package.get(GROUPS, []) for ref in group.get(REFS, []) if RESIDREF in ref]


def remove_ref_from_inmem_package(package: dict, ref_id: str) -> bool:
    """Removes the reference with ref_id from non-root groups.

    If there is nothing left in that group then the group and its reference in root group is also removed.
    If the removed item was the last item then returns

    :param package: The package dictionary to modify
    :param ref_id: Id of the reference to be removed
    :return: True if there are still references in the package, False otherwise
    """

    groups_to_be_removed = set()
    non_root_groups = [group for group in package.get(GROUPS, []) if group.get(GROUP_ID) != ROOT_GROUP]
    for non_rg in non_root_groups:
        refs = [r for r in non_rg.get(REFS, []) if r.get(RESIDREF, "") != ref_id]
        if len(refs) == 0:
            groups_to_be_removed.add(non_rg.get(GROUP_ID))
        non_rg[REFS] = refs

    if len(groups_to_be_removed) > 0:
        root_group = [group for group in package.get(GROUPS, []) if group.get(GROUP_ID) == ROOT_GROUP][0]
        refs = [r for r in root_group.get(REFS, []) if r.get(ID_REF) not in groups_to_be_removed]
        root_group[REFS] = refs
        removed_groups = [group for group in package.get(GROUPS, []) if group.get(GROUP_ID) not in groups_to_be_removed]
        package[GROUPS] = removed_groups

        # return if the package has any items left in it
        return len(refs) > 0

    # still has items in the package
    return True


async def replace_ref_in_package(package: dict, old_ref_id: str, new_ref_id: str | None) -> None:
    """Locates the reference with the old_ref_id and replaces with the new_ref_id

    :param package: The package dictionary to modify
    :param old_ref_id: Old reference id
    :param new_ref_id: New reference id
    """

    non_root_groups = (group for group in package.get(GROUPS, []) if group.get(GROUP_ID) != ROOT_GROUP)
    for g in (ref for group in non_root_groups for ref in group.get(REFS, [])):
        if g.get(RESIDREF, "") == old_ref_id:
            new_item = await get_resource_service("archive").find_one_async(req=None, _id=new_ref_id)
            g[RESIDREF] = new_ref_id
            g["guid"] = new_ref_id
            g[VERSION] = new_item[VERSION]
