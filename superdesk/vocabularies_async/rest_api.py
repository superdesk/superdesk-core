# TODO-ASYNC: Update this to use our own converter
from eve.methods.common import serialize_value

from superdesk.core.types import Request, RestGetResponse
from superdesk.core import json
from superdesk.core.resources import ResourceRestEndpoints


# TODO(petr): add api to specify vocabulary schema
vocab_schema = {
    "crop_sizes": {
        "width": {"type": "integer"},
        "height": {"type": "integer"},
    }
}


class VocabulariesRestEndpoints(ResourceRestEndpoints):
    async def on_fetched_item(self, request: Request, doc: dict) -> None:
        """
        Overriding to filter out inactive vocabularies and pops out 'is_active' property from the response.
        """
        self._filter_inactive_vocabularies(doc)
        self._cast_items(doc)

    async def on_fetched(self, request: Request, doc: RestGetResponse) -> None:
        """Overriding to filter out inactive vocabularies and pops out 'is_active' property from the response.

        It keeps it when requested for manageable vocabularies.
        """

        where_arg = request.get_url_arg("where")
        if where_arg:
            where_clause = json.loads(where_arg)
            if where_clause.get("type") == "manageable":
                return

        for item in doc.get("_items", []):
            self._filter_inactive_vocabularies(item)
            self._cast_items(item)

    def _filter_inactive_vocabularies(self, item: dict) -> None:
        vocs = item["items"]
        active_vocs = (
            {k: voc[k] for k in voc.keys() if k != "is_active"} for voc in vocs if voc.get("is_active", True)
        )

        item["items"] = list(active_vocs)

    def _cast_items(self, vocab: dict) -> None:
        """Cast values in vocabulary items using predefined schema.

        :param vocab
        """
        schema = vocab_schema.get(vocab.get("_id") or "", {})
        for item in vocab.get("items", []):
            for field, field_schema in schema.items():
                if field in item:
                    item[field] = serialize_value(field_schema["type"], item[field])
