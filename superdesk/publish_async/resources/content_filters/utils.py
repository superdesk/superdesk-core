import logging

from bson import ObjectId

from superdesk.types import ContentFiltersResource


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
