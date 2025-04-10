from typing import Protocol
from types import TracebackType
from io import BytesIO
from datetime import datetime

from bson import ObjectId
from quart.wrappers.response import ResponseBody


class SuperdeskFile(BytesIO):
    _name: str
    filename: str
    content_type: str
    length: int
    upload_date: datetime
    md5: str

    @property
    def name(self):
        return self._name


class AsyncBuffer(Protocol):
    length: int

    async def read(self, size: int = -1) -> bytes:
        ...

    def seek(self, offset: int, whence: int = 0) -> int:
        ...

    def tell(self) -> int:
        ...


class SuperdeskAsyncFile(SuperdeskFile, ResponseBody):
    DEFAULT_CHUNK_SIZE = 1024 * 256
    buffer: AsyncBuffer

    def __init__(
        self,
        buffer: AsyncBuffer,
        name: str,
        content_type: str,
        filename: str,
        length: int,
        upload_date: datetime,
        md5: str,
        media_id: str | ObjectId,
        metadata: dict | None,
        begin: int = 0,
        end: int | None = None,
    ):
        super().__init__()
        self.buffer = buffer
        self.content_type = content_type
        self.length = length
        self._name = name
        self.filename = filename
        self.metadata = metadata
        self.upload_date = upload_date
        self.md5 = md5
        self._id = media_id
        self.begin = begin
        self.end = end if end is not None else length
        self.buffer_size = self.DEFAULT_CHUNK_SIZE

    def __aiter__(self):
        return self

    async def __aexit__(self, exc_type: type, exc_value: BaseException, tb: TracebackType) -> None:
        pass

    def seekable(self) -> bool:
        if hasattr(self.buffer, "seekable"):
            return self.buffer.seekable()
        if hasattr(self.buffer, "seek"):
            return True
        return False

    async def __aenter__(self):
        if self.seekable():
            self.buffer.seek(self.begin)
        return self

    async def __anext__(self) -> bytes:
        """Return the next chunk of the file."""

        if self.end is None or not self.seekable():
            current_chunk = await self.buffer.read(self.buffer_size)
        else:
            current = self.buffer.tell()
            if current >= self.end:
                raise StopAsyncIteration

            read_size = min(self.buffer_size, self.end - current)
            current_chunk = await self.read(read_size)

        if current_chunk:
            return current_chunk
        raise StopAsyncIteration

    async def read(self, size: int = -1) -> bytes:  # type: ignore[override]
        return await self.buffer.read(size)

    async def make_conditional(self, begin: int, end: int | None) -> int:
        return self.length
