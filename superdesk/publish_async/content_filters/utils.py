import logging

from bson import ObjectId
from quart_babel import gettext

from superdesk.types import ContentFiltersResource, FilterConditionsResource
from superdesk.errors import SuperdeskApiError
from superdesk.publish_async.publish_cache import PublishCache
from apps.content_filters.filter_condition.filter_condition import FilterCondition


logger = logging.getLogger(__name__)


def item_matches_content_filter(item: dict, content_filter: ContentFiltersResource | None, cache: bool = True) -> bool:
    if not content_filter:
        return True
    elif cache is False:
        return _check_item_matches_content_filter(item, content_filter, cache)

    publish_cache = PublishCache.get()
    cache_id = publish_cache.generate_cache_id("filter-match", str(content_filter.id) or content_filter.name, item)
    if cache_id not in publish_cache.filter_result_cache:
        publish_cache.filter_result_cache[cache_id] = _check_item_matches_content_filter(item, content_filter)

    return publish_cache.filter_result_cache[cache_id]


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


async def content_filter_to_mongo_query(doc: ContentFiltersResource) -> dict:
    content_filter_service = ContentFiltersResource.get_service()
    filter_condition_service = FilterConditionsResource.get_service()
    expressions = []
    for expression in doc.content_filter or []:
        filter_conditions = []
        for filter_id in expression.expression.fc or []:
            current_filter_item = await filter_condition_service.find_by_id(filter_id)
            if not current_filter_item:
                # Should not happen, as we have validation on the model to prevent this
                continue

            current_filter_condition = FilterCondition.parse(current_filter_item.to_dict())
            mongo_query = current_filter_condition.get_mongo_query()
            filter_conditions.append(mongo_query)

        for filter_id in expression.expression.pf or []:
            current_content_filter = await content_filter_service.find_by_id(filter_id)
            if not current_content_filter:
                # Should not happen, as we have validation on the model to prevent this
                continue
            mongo_query = await content_filter_to_mongo_query(current_content_filter)
            filter_conditions.append(mongo_query)

        if len(filter_conditions) > 1:
            expressions.append({"$and": filter_conditions})
        else:
            expressions.extend(filter_conditions)

    if len(expressions) > 1:
        return {"$or": expressions}
    else:
        return expressions[0]


async def content_filter_to_elastic_query(doc: ContentFiltersResource, matching: bool = True) -> dict:
    content_filter_service = ContentFiltersResource.get_service()
    filter_condition_service = FilterConditionsResource.get_service()
    expressions_list: list[dict] = []
    if matching:
        expressions = {"should": expressions_list}
    else:
        expressions = {"must_not": expressions_list}

    for expression in doc.content_filter or []:
        filter_conditions = {"must": [], "must_not": [{"term": {"state": "spiked"}}]}
        for filter_id in expression.expression.fc or []:
            current_filter_item = await filter_condition_service.find_by_id(filter_id)
            if not current_filter_item:
                # Should not happen, as we have validation on the model to prevent this
                continue
            current_filter_condition = FilterCondition.parse(current_filter_item.to_dict())
            elastic_query = current_filter_condition.get_elastic_query()
            if current_filter_condition.contains_not():
                filter_conditions["must_not"].append(elastic_query)
            else:
                filter_conditions["must"].append(elastic_query)

        for filter_id in expression.expression.pf or []:
            current_content_filter = await content_filter_service.find_by_id(filter_id)
            if not current_content_filter:
                # Should not happen, as we have validation on the model to prevent this
                continue
            elastic_query = await content_filter_to_elastic_query(current_content_filter)
            filter_conditions["must"].append(elastic_query)

        expressions_list.append({"bool": filter_conditions})

    return {"bool": expressions}


def _check_item_matches_content_filter(item: dict, content_filter: ContentFiltersResource, cache: bool = True) -> bool:
    if not content_filter.content_filter:
        return False

    for index, expression in enumerate(content_filter.content_filter):
        if not expression.expression:
            raise SuperdeskApiError.badRequestError(
                gettext("Filter statement {index} does not have a filter condition").format(index=index + 1)
            )

        if expression.expression.fc:
            if not _does_filter_condition_match(item, content_filter, expression.expression.fc, cache):
                continue
        if expression.expression.pf:
            if not _does_content_filter_match(item, expression.expression.pf, cache):
                continue

        return True

    return False


def _does_filter_condition_match(
    item: dict, content_filter: ContentFiltersResource, filter_condition_ids: list[ObjectId], cache: bool = True
) -> bool:
    publish_cache = PublishCache.get()
    for filter_condition_id in filter_condition_ids:
        cache_id = publish_cache.generate_cache_id("filter-condition-match", str(filter_condition_id), item)
        if cache is False or cache_id not in publish_cache.filter_result_cache:
            filter_condition_item = publish_cache.filter_conditions.get(filter_condition_id)
            if not filter_condition_item:
                logger.error(f"Missing filter condition {filter_condition_id} in content filter {content_filter.name}")
                return False

            filter_condition = FilterCondition.parse(filter_condition_item.to_dict())
            filter_result = filter_condition.does_match(item)
            if cache is False:
                if filter_result is False:
                    return False
            else:
                publish_cache.filter_result_cache[cache_id] = filter_result

        if publish_cache.filter_result_cache[cache_id] is False:
            return False

    return True


def _does_content_filter_match(item: dict, content_filter_ids: list[ObjectId], cache: bool = True) -> bool:
    publish_cache = PublishCache.get()

    for content_filter_id in content_filter_ids:
        cache_id = publish_cache.generate_cache_id("content-filter-match", str(content_filter_id), item)
        if cache is False or cache_id not in publish_cache.filter_result_cache:
            content_filter = publish_cache.content_filters.get(content_filter_id)
            filter_result = item_matches_content_filter(item, content_filter, cache)
            if cache is False:
                if filter_result is False:
                    return False
            else:
                publish_cache.filter_result_cache[cache_id] = filter_result

        if publish_cache.filter_result_cache[cache_id] is False:
            return False

    return True
