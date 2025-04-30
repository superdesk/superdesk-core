from typing import TYPE_CHECKING
from typing_extensions import Self

from pymongo.cursor_shared import _Hint as MongoCursorHint
from motor.motor_asyncio import AsyncIOMotorCursor


if TYPE_CHECKING:

    class MongoAsyncEveCursor(AsyncIOMotorCursor):
        # Adding the ``count`` method to the cursor, as our ``EveBackend`` adds it
        async def count(self) -> int:
            ...  # type: ignore[empty-body]

        # Make sure ``sort`` function returns our cursor class
        def sort(self, key_or_list: MongoCursorHint, direction: int | str | None = None) -> "MongoAsyncEveCursor":
            ...  # type: ignore[empty-body]

        # Seems like ``motor-types`` incorrectly assumes length is not optional
        # compared to the ``motor`` library where it's optional
        async def to_list(self, length: int | None = None) -> list[dict]:  # type: ignore[override]
            ...  # type: ignore[empty-body]

else:
    MongoAsyncEveCursor = AsyncIOMotorCursor


class AsyncListCursor:
    """Wrapper for a python list as a cursor."""

    _index: int
    _limit: int
    docs: list[dict]

    def __init__(self, docs: list[dict] | None = None):
        self._index = 0
        self._limit = -1
        self.docs = docs or []

    def __aiter__(self):
        return self

    async def __anext__(self) -> dict:
        item = await self.next()
        if item is not None:
            return item
        raise StopAsyncIteration

    async def next(self) -> dict | None:
        if self._index >= self._limit:
            return None

        try:
            doc = self.docs[self._index]
            self._index += 1
            return doc
        except (IndexError, KeyError, TypeError):
            self._index = 0
            return None

    async def to_list(self, length: int | None = None) -> list[dict]:
        if length is None and self._limit >= 0:
            length = self._limit
        return self.docs if length is None else self.docs[:length]

    def rewind(self) -> None:
        """Rewind cursor to the beginning."""
        self._index = 0

    async def count(self, **kwargs) -> int:
        """Get hits count."""
        return len(self.docs)

    def extra(self, response) -> None:
        pass

    def skip(self, skip: int) -> Self:
        self._index += skip
        return self

    def limit(self, limit: int) -> Self:
        self._limit = limit
        return self


class ElasticAsyncEveCursor(AsyncListCursor):
    """Search results cursor.

    Note: Adds methods to provide similar interface to MongoDB's AsyncIOMotorCursor
    """

    hits: dict
    no_hits = {"hits": {"total": 0, "hits": []}}

    def __init__(self, hits: dict | None = None, docs: list[dict] | None = None):
        """Parse hits into docs."""
        super().__init__(docs)
        self.hits = hits if hits else self.no_hits

    async def count(self, **kwargs) -> int:
        """Get hits count."""
        hits = self.hits.get("hits")
        if hits:
            total = hits.get("total")
            if isinstance(total, int):
                return total
            elif isinstance(total, dict) and total.get("value"):
                return int(total["value"])
        return 0

    def extra(self, response) -> None:
        """Add extra info to response"""
        if "facets" in self.hits:
            response["_facets"] = self.hits["facets"]
        if "aggregations" in self.hits:
            response["_aggregations"] = self.hits["aggregations"]


AsyncEveCursor = AsyncListCursor | MongoAsyncEveCursor | ElasticAsyncEveCursor
