from superdesk.types.vocabularies import CVItem, VocabulariesResourceModel


async def get_cv_items(
    cv_id: str,
    qcode: str | None = None,
    is_active: bool = True,
    name: str | None = None,
    lang: str | None = None,
) -> list[CVItem]:
    """
    Return `items` with specified filters from the CV with specified `cv_id`.
    If `lang` is provided then `name` is looked in `items.translations.name.{lang}`,
    otherwise `name` is looked in `items.name`.

    :param cv_id: custom vocabulary cv_id
    :param qcode: items.qcode filter
    :param is_active: items.is_active filter
    :param name: items.name filter
    :param lang: items.lang filter
    :return: items list
    """

    projection: dict = {}
    lookup = {"_id": cv_id}

    if qcode:
        elem_match = projection.setdefault("items", {}).setdefault("$elemMatch", {})
        elem_match["qcode"] = qcode

    # if `lang` is provided `name` is looked in `translations.name.{lang}`
    if name and lang:
        elem_match = projection.setdefault("items", {}).setdefault("$elemMatch", {})
        elem_match[f"translations.name.{lang}"] = {
            "$regex": r"^{}$".format(name),
            # case-insensitive
            "$options": "i",
        }
    elif name:
        elem_match = projection.setdefault("items", {}).setdefault("$elemMatch", {})
        elem_match["name"] = {
            "$regex": r"^{}$".format(name),
            # case-insensitive
            "$options": "i",
        }

    cursor = await VocabulariesResourceModel.get_service().find(lookup, projection=projection)

    try:
        voc = await cursor.next()
    except StopAsyncIteration:
        voc = None

    if voc is None:
        return []

    items = voc.items

    # $elemMatch projection contains only the first element matching the condition,
    # that"s why `is_active` filter is filtered via python
    if is_active is not None:
        items = [i for i in items if i.is_active == is_active]

    def format_item(item: CVItem) -> CVItem:
        try:
            del item.is_active
        except KeyError:
            pass
        item.scheme = cv_id
        return item

    items = list(map(format_item, items))

    return items


async def get_languages() -> list[CVItem]:
    return await get_cv_items("languages")
