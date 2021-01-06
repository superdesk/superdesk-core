import bson
import superdesk

from flask import abort, request, json
from superdesk.utc import utcnow
from superdesk.utils import ListCursor
from apps.search_providers.registry import registered_search_providers
from apps.io.search_ingest import SearchIngestService
from superdesk.metadata.item import get_schema


PROXY_ENDPOINT = "search_providers_proxy"


class SearchProviderProxyResource(superdesk.Resource):
    schema = {
        "guid": {"type": "string", "required": True},
        "desk": superdesk.Resource.rel("desks", False, nullable=True),
        "repo": superdesk.Resource.rel("search_providers", False, nullable=True),
        "stage": superdesk.Resource.rel("stages", False, nullable=True),
        "fetch_endpoint": {"type": "string", "readonly": True},
        "search_provider": {"type": "string", "readonly": True},
        "_fetchable": {"type": "boolean", "readonly": True},
    }
    schema.update(get_schema())

    resource_methods = ["GET", "POST"]
    privileges = {"POST": "archive"}


class SearchProviderProxyService(SearchIngestService):
    """Search Provider Proxy.

    It will forward requests to specific SearchProvider instance.

    Old implementations will get forwarded to its service.
    """

    def get_provider(self, provider_id=None, req=None):
        if not provider_id:
            provider_id = req.args.get("repo") if req else request.args.get("repo")
        if provider_id is None:
            abort(400)
        try:
            bson.ObjectId(provider_id)
        except bson.errors.InvalidId:
            return provider_id
        provider = superdesk.get_resource_service("search_providers").find_one(req=None, _id=provider_id)
        if not provider:
            abort(400)
        if provider.get("is_closed"):
            abort(400)
        return provider

    def _get_service(self, provider):
        if isinstance(provider, str):
            return provider if "," not in provider and provider else "search"
        provider_data = registered_search_providers[provider["search_provider"]]
        try:
            return provider_data["endpoint"]
        except KeyError:
            return provider_data["class"](provider)

    def get(self, req, lookup):
        """Search using provider."""
        provider = self.get_provider(req=req)
        service = self._get_service(provider)
        if isinstance(service, str):
            return superdesk.get_resource_service(service).get(req, lookup)
        query = self._get_query(req)
        params = json.loads(req.args["params"]) if req.args.get("params") else {}
        try:
            items = service.find(query, params)
        except TypeError:  # BC
            items = service.find(query)
        if isinstance(items, list):
            items = ListCursor(items)
        for item in items:
            self._set_item_defaults(item, provider)
        return items

    def create(self, docs, **kwargs):
        """Archive items from provider."""
        provider = self.get_provider()
        service = self._get_service(provider)
        if isinstance(service, str):
            return superdesk.get_resource_service(service).create(docs, **kwargs)
        return super().create(docs, **kwargs)

    def fetch(self, guid):
        """Fetch single item from provider to archive it."""
        provider = self.get_provider()
        service = self._get_service(provider)
        if isinstance(service, str):
            return superdesk.get_resource_service(service).fetch(guid)
        item = service.fetch(guid)
        self._set_item_defaults(item, provider)
        return item

    def fetch_rendition(self, rendition, item):
        """Fetch binary from provider."""
        provider = self.get_provider(provider_id=item.get("ingest_provider"))
        service = self._get_service(provider)
        if isinstance(service, str):
            return superdesk.get_resource_service(service).fetch_rendition(self, rendition)
        return service.fetch_file(rendition.get("href"), rendition=rendition, item=item)

    def _set_item_defaults(self, item, provider):
        """Add default values to external items."""
        now = utcnow()
        item.setdefault("_id", item.get("guid") or bson.ObjectId())
        item.setdefault("_type", "externalsource")
        item.setdefault("type", "picture")
        item.setdefault("pubstatus", "usable")
        item.setdefault("firstcreated", now)
        item.setdefault("versioncreated", now)
        item.setdefault("fetch_endpoint", PROXY_ENDPOINT)
        item.setdefault("ingest_provider", str(provider["_id"]))
