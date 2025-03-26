from typing import Dict, Any

from quart_babel import gettext

from superdesk.core.resources import AsyncResourceService

from superdesk.errors import SuperdeskApiError
from superdesk.types import ProductsResource, ProductTypes, SubscribersResource


class ProductsService(AsyncResourceService[ProductsResource]):
    async def on_update(self, updates: Dict[str, Any], original: ProductsResource) -> None:
        await self._validate_product_type(updates, original)
        await super().on_update(updates, original)

    async def on_delete(self, doc: ProductsResource) -> None:
        # Check if any subscriber is using the product
        names = await SubscribersResource.get_names(
            {"$or": [{"products": {"$in": [doc.id]}}, {"api_products": {"$in": [doc.id]}}]}
        )
        if names:
            raise SuperdeskApiError.badRequestError(
                message=gettext("Product is used by the subscriber(s): {names}").format(names=", ".join(names))
            )

        await super().on_delete(doc)

    async def _validate_product_type(self, updates: dict, original: ProductsResource) -> None:
        """Validates product type field. Raises Bad Request error for following conditions:
        1. new product type is direct and product is assigned as api product.
        2. new product type is api and product is assigned as direct product.

        :param dict updates: updates to the product
        :param dict original: original of the product
        """

        if updates.get("product_type", ProductTypes.BOTH) == original.product_type:
            # If ``product_type`` has not changed, no need to validate
            return

        if updates.get("product_type") == ProductTypes.DIRECT:
            names = await SubscribersResource.get_names({"api_products": original.id})
            if names:
                raise SuperdeskApiError.badRequestError(
                    message=gettext("Product is used for API publishing for the subscriber(s): {subscribers}").format(
                        subscribers=", ".join(names)
                    )
                )
        elif updates.get("product_type") == ProductTypes.API:
            names = await SubscribersResource.get_names({"products": original.id})
            if names:
                raise SuperdeskApiError.badRequestError(
                    message=gettext(
                        "Product is used for direct publishing for the subscriber(s): {subscribers}"
                    ).format(subscribers=", ".join(names))
                )
