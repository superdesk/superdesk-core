from elasticsearch import AsyncElasticsearch, exceptions as elastic_exceptions
from elasticsearch.helpers import async_bulk

from eve_elastic import Elastic, ElasticJSONSerializer, InvalidSearchString
from eve_elastic.elastic import fix_query, RESOURCE_FIELD

from superdesk.resource_fields import ID_FIELD

from .cursors import ElasticAsyncEveCursor


def get_es_async(url: str, **kwargs) -> AsyncElasticsearch:
    """Create async elasticsearch instance.

    :param url: elasticsearch url
    """

    urls = [url] if isinstance(url, str) else url
    kwargs.setdefault("serializer", ElasticJSONSerializer())
    es = AsyncElasticsearch(urls, **kwargs)
    return es


class ElasticAsync(Elastic):
    es_async: AsyncElasticsearch

    def init_app(self, app):
        super().init_app(app)
        self.es_async = get_es_async(app.config["ELASTICSEARCH_URL"], **self.kwargs)

    def elastic_async(self, resource: str) -> AsyncElasticsearch:
        """Get ElasticSearch instance for given resource."""
        px = self._resource_prefix(resource)

        if px not in self.elastics:
            url = self._resource_config(resource, "URL")
            assert url, "no url for %s" % px
            self.elastics[px] = get_es_async(url, **self.kwargs)

        return self.elastics[px]

    def _parse_hits_async(self, hits, resource):
        return ElasticAsyncEveCursor(hits, self.get_hits_docs(hits, resource))

    async def find(self, resource, req, sub_resource_lookup, **kwargs) -> tuple[ElasticAsyncEveCursor, int]:
        """Find documents for resource"""

        search_args = self.get_find_kwargs(resource, req, sub_resource_lookup)

        try:
            hits = await self.elastic_async(resource).search(**search_args)
        except elastic_exceptions.RequestError as e:
            if e.status_code == 400 and "No mapping found for" in e.error:
                hits = {}
            elif e.status_code == 400 and "SearchParseException" in e.error:
                raise InvalidSearchString
            else:
                raise

        cursor = self._parse_hits_async(hits, resource)
        return cursor, await cursor.count()

    async def find_one(self, resource, req, **lookup) -> dict | None:
        if ID_FIELD in lookup:
            return await self._find_by_id(
                resource=resource,
                _id=lookup[ID_FIELD],
                parent=lookup.get("parent"),
            )

        search_args = self.get_find_one_kwargs(resource, **lookup)
        try:
            hits = await self.elastic_async(resource).search(**search_args)
            docs = self._parse_hits_async(hits, resource)
            return await docs.next()
        except elastic_exceptions.NotFoundError:
            return None

    async def find_one_raw(self, resource, **lookup):
        item_id = lookup.get(ID_FIELD)
        return await self._find_by_id(resource=resource, _id=item_id)

    async def find_list_of_ids(self, resource, ids, client_projection=None):
        """Find documents by ids."""
        args = self._es_args(resource)
        return self._parse_hits_async(self.elastic_async(resource).mget(body={"ids": ids}, **args), resource)

    async def insert(self, resource, doc_or_docs, **kwargs):
        """Insert document, it must be new if there is ``_id`` in it."""
        ids = []
        es_args = self._es_args(resource)
        es_args.update(kwargs)
        for doc in doc_or_docs:
            _id = doc.pop("_id", None)
            body = self._prepare_for_storage(resource, doc, es_args)
            res = await self.elastic_async(resource).index(body=body, id=_id, **es_args)
            doc.setdefault("_id", res.get("_id", _id))
            ids.append(doc.get("_id"))
        await self._refresh_resource_index_async(resource)
        return ids

    async def bulk_insert(self, resource, docs, **kwargs):
        """Bulk insert documents."""
        kwargs.update(self._es_args(resource))
        parent_type = self._get_parent_type(resource)
        actions = []
        for doc in docs:
            doc[RESOURCE_FIELD] = resource
            if parent_type and doc.get(parent_type.get("field")):
                doc["_parent"] = doc.get(parent_type.get("field"))
            action = {"_source": self._prepare_for_storage(resource, doc, kwargs)}
            if doc.get("_id"):
                action["_id"] = doc["_id"]
            actions.append(action)
        res = await async_bulk(self.elastic_async(resource), actions, stats_only=False, **kwargs)
        await self._refresh_resource_index_async(resource)
        return res

    async def update(self, resource, id_, updates, original=None):
        """Update document in index."""
        args = self._es_args(resource, refresh=True)
        if self._get_retry_on_conflict():
            args["retry_on_conflict"] = self._get_retry_on_conflict()
        doc = self._prepare_for_storage(resource, updates, args)
        return await self.elastic_async(resource).update(id=id_, body={"doc": doc}, **args)

    async def replace(self, resource, id_, document, original=None):
        """Replace document in index."""
        args = self._es_args(resource, refresh=True)
        doc = self._prepare_for_storage(resource, document, args)
        return await self.elastic_async(resource).index(body=doc, id=id_, **args)

    async def remove(self, resource, lookup=None, parent=None, **kwargs):
        """Remove docs for resource.

        :param resource: resource name
        :param lookup: filter
        :param parent: parent id
        """
        kwargs.update(self._es_args(resource))
        if parent:
            kwargs["parent"] = parent

        if lookup:
            if lookup.get("_id"):
                try:
                    return await self.elastic_async(resource).delete(id=lookup.get("_id"), refresh=True, **kwargs)
                except elastic_exceptions.NotFoundError:
                    return
        return ValueError("there must be `lookup._id` specified")

    async def is_empty(self, resource):
        """Test if there is no document for resource.

        :param resource: resource name
        """
        args = self._es_args(resource)
        res = await self.elastic_async(resource).count(body={"query": {"match_all": {}}}, **args)
        return res.get("count", 0) == 0

    async def search(self, query, resources, params=None):
        """Search multiple resources at the same time.

        They must use all same elastic instance and should be same schema.
        """

        default_params = self._get_default_search_params()

        if params is not None:
            default_params.update(params)

        params = default_params

        if isinstance(resources, str):
            resources = resources.split(",")
        index = [self._resource_index(resource) for resource in resources]
        try:
            hits = await self.elastic_async(resources[0]).search(body=fix_query(query), index=index, **params)
            return self._parse_hits_async(hits, resources[0])
        except elastic_exceptions.RequestError:
            raise

    async def _refresh_resource_index_async(self, resource, force=False):
        """Refresh index for given resource.

        :param resource: resource name
        """
        if self._resource_config(resource, "FORCE_REFRESH", True) or force:
            await self.elastic_async(resource).indices.refresh(index=self._resource_index(resource))

    async def _find_by_id(self, resource, _id, parent=None):
        """Find the document by Id. If parent is not provided then on
        routing exception try to find using search.
        """

        def is_found(hit):
            if "exists" in hit:
                hit["found"] = hit["exists"]
            return hit.get("found", False)

        args = self._es_args(resource)
        try:
            # set the parent if available
            if parent:
                args["parent"] = parent

            hit = await self.elastic_async(resource).get(id=_id, **args)

            if not is_found(hit):
                return

            docs = self._parse_hits_async({"hits": {"hits": [hit]}}, resource)
            return await docs.next()

        except elastic_exceptions.NotFoundError:
            return
        except elastic_exceptions.TransportError as tex:
            if tex.error == "routing_missing_exception" or "RoutingMissingException" in tex.error:
                # search for the item
                args = self._es_args(resource)
                query = {"query": {"bool": {"must": [{"term": {"_id": _id}}]}}}
                try:
                    args["size"] = 1
                    hits = await self.elastic_async(resource).search(body=fix_query(query), **args)
                    docs = self._parse_hits_async(hits, resource)
                    return await docs.next()
                except elastic_exceptions.NotFoundError:
                    return
