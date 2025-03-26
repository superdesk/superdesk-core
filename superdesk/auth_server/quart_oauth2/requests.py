from collections import defaultdict
from functools import cached_property

from quart.wrappers import Request
from werkzeug.datastructures import CombinedMultiDict, MultiDict
from authlib.oauth2.rfc6749 import OAuth2Request, JsonRequest


class QuartOAuth2Request(OAuth2Request):
    _request: Request
    _form: MultiDict
    _values: CombinedMultiDict

    def __init__(self, request: Request):
        super().__init__(request.method, request.url, None, request.headers)
        self._request = request
        self._form = MultiDict()
        self._values = CombinedMultiDict()

    async def init_request_data(self):
        self._form = await self._request.form
        self._values = await self._request.values

    @property
    def args(self):
        return self._request.args

    @property
    def form(self):
        return self._form

    @property
    def data(self):
        return self._values

    @cached_property
    def datalist(self):
        values = defaultdict(list)
        for k in self.data:
            values[k].extend(self.data.getlist(k))
        return values


class QuartJsonRequest(JsonRequest):
    _json: dict

    def __init__(self, request: Request):
        super().__init__(request.method, request.url, None, request.headers)
        self._request = request
        self._json = {}

    async def init_request_data(self):
        self._json = await self._request.get_json()

    @property
    def data(self):
        return self._json
