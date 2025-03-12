from superdesk.types import ContentFiltersResource, FilterConditionsResource, PublishRequest
from superdesk.resource_fields import ID_FIELD, ITEM_TYPE
from superdesk.publish_async.filters import BasePublishExchangeFilter
from apps.content_filters.filter_condition.filter_condition import FilterCondition


def item_matches_content_filter(item: dict, content_filter: ContentFiltersResource | None) -> bool:
    request = PublishRequest(
        item=item,
        item_id=item[ID_FIELD],
        item_type=item.get(ITEM_TYPE) or "text",
        operation="publish",
        published_state="published",
    )
    return BasePublishExchangeFilter().content_filter_matches_item(request, content_filter)


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
