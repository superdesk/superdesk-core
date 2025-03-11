from typing import Any

from quart_babel import gettext
from bson import ObjectId

from superdesk.core.resources import AsyncResourceService

from superdesk.types import FilterConditionsResource, ContentFiltersResource
from superdesk.errors import SuperdeskApiError

from .filter_condition_params import get_available_filter_params


class FilterConditionsService(AsyncResourceService[FilterConditionsResource]):
    async def validate_create(self, doc: FilterConditionsResource) -> None:
        await super().validate_create(doc)
        await self._check_equals(doc, True)
        await self._check_parameters(doc)

    async def validate_update(self, updates: dict, original: FilterConditionsResource, etag: str | None) -> dict:
        updated_dict = await super().validate_update(updates, original, etag)
        updated = FilterConditionsResource.from_dict(updated_dict)
        await self._check_equals(updated, False)
        await self._check_parameters(updated)
        return updated_dict

    async def delete(self, doc: FilterConditionsResource, etag: str | None = None):
        referenced_filters = await self._get_referenced_filter_conditions(doc.id)
        if len(referenced_filters) > 0:
            references = ",".join([pf.name for pf in referenced_filters])
            raise SuperdeskApiError.badRequestError(
                gettext(f"Filter condition has been referenced in content filter: {references}")
            )
        await super().delete(doc)

    async def _get_referenced_filter_conditions(self, doc_id: ObjectId) -> list[ContentFiltersResource]:
        return await (
            await ContentFiltersResource.get_service().search({"content_filter.expression.fc": {"$in": [doc_id]}})
        ).to_list()

    async def _check_equals(self, doc: FilterConditionsResource, creating: bool) -> None:
        """Checks if any of the filter conditions in the docs already exists

        :param docs: List of filter conditions to be tested
        :raises SuperdeskApiError: if any of the filter conditions in the docs
        already exists
        """

        async for existing_doc in await self.search({"field": doc.field, "operator": doc.operator}):
            if not creating and doc.id == existing_doc.id:
                continue
            elif self._are_equal(doc, existing_doc):
                raise SuperdeskApiError.badRequestError(
                    gettext(f"Filter condition:{existing_doc.name} has identical settings")
                )

    async def _check_parameters(self, doc: FilterConditionsResource) -> None:
        parameters = await get_available_filter_params()
        parameter = [param for param in parameters if param.field == doc.field]
        if not parameter or len(parameter) == 0:
            raise SuperdeskApiError.badRequestError(
                gettext(f"Filter condition:{doc.name} has unidentified field: {doc.field}")
            )
        if doc.operator not in parameter[0].operators:
            print(parameter[0].operators)
            raise SuperdeskApiError.badRequestError(
                gettext(f"Filter condition:{doc.name} has unidentified operator: {doc.operator}")
            )

    def _are_equal(self, fc1: FilterConditionsResource, fc2: FilterConditionsResource) -> bool:
        def get_comparer(fc: FilterConditionsResource):
            return "".join(sorted(fc.value.upper())) if "," in fc.value else fc.value.upper()

        return all([fc1.field == fc2.field, fc1.operator == fc2.operator, get_comparer(fc1) == get_comparer(fc2)])
