import logging

from bson import ObjectId

from superdesk.types import ContentFiltersResource

from ..filters import BasePublishExchangeFilter
from .common import get_publish_request_from_item


logger = logging.getLogger(__name__)


async def get_content_filters_by_filter_condition(filter_condition_id: ObjectId) -> list[ContentFiltersResource]:
    lookup = {"content_filter.expression.fc": {"$in": [filter_condition_id]}}
    content_filters = await (await ContentFiltersResource.get_service().search(lookup)).to_list()
    return await _get_referenced_content_filters(content_filters, None)


async def _get_content_filters_by_content_filter(content_filter_id) -> list[ContentFiltersResource]:
    lookup = {"content_filter.expression.pf": {"$in": [content_filter_id]}}
    return await ContentFiltersResource.get_service().get_all_list(lookup)


async def _get_referenced_content_filters(
    content_filters: list[ContentFiltersResource], pf_list: list[ContentFiltersResource] | None
) -> list[ContentFiltersResource]:
    if not pf_list:
        pf_list = []

    for pf in content_filters:
        pf_list.append(pf)
        references = await _get_content_filters_by_content_filter(pf.id)
        if references and len(references) > 0:
            return await _get_referenced_content_filters(references, pf_list)
    return pf_list


def item_matches_content_filter(item: dict, content_filter: ContentFiltersResource | dict | None) -> bool:
    """Returns boolean if the supplied item matches the content_filter

    Note: Make sure to initialise the PublishCache before running this function
    """

    if content_filter is None:
        return True
    elif isinstance(content_filter, dict):
        content_filter.setdefault("_id", ObjectId())
        content_filter.setdefault("name", "<in_memory_filter>")
        content_filter = ContentFiltersResource.from_dict(content_filter)

    return BasePublishExchangeFilter().content_filter_matches_item(get_publish_request_from_item(item), content_filter)
