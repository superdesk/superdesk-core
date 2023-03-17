import hermes
import hermes.backend
import hermes.backend.redis
import hermes.backend.inprocess

from urllib.parse import urlparse

from flask import current_app
from superdesk import json_utils
from superdesk.logging import logger


class SuperdeskMangler(hermes.Mangler):
    """Implements encoding/decoding for Superdesk data - so handles ObjectIds, dates etc."""

    def hash(self, value):
        try:
            encoded_value = value.encode("utf-8")
        except AttributeError:
            encoded_value = value
        return super().hash(encoded_value)

    def dumps(self, value):
        return json_utils.dumps(value)

    def loads(self, value):
        return json_utils.loads(value)


class SuperdeskCacheBackend(hermes.backend.AbstractBackend):
    """Proxy for hermes cache backend.

    It will only initialize proper cache backend when some cache method is called,
    so we can use @cache decorator before the app starts.

    Later it reads ``CACHE_URL`` config to figure out if we want to use redis backend
    or memcached.
    """

    def init_app(self, app):
        if not hasattr(app, "extensions"):
            app.extensions = {}

        if not app.extensions.get("superdesk_cache"):
            cache_url = app.config.get("CACHE_URL", "")
            if "redis" in cache_url or "unix" in cache_url:
                parsed_url = urlparse(cache_url)
                assert parsed_url.hostname
                app.extensions["superdesk_cache"] = hermes.backend.redis.Backend(
                    self.mangler,
                    host=parsed_url.hostname,
                    password=parsed_url.password if parsed_url.password else None,
                    port=int(parsed_url.port) if parsed_url.port else 6379,
                    db=int(parsed_url.path[1:]) if parsed_url.path else 0,
                )
                logger.info("using redis cache backend")
            else:
                app.extensions["superdesk_cache"] = hermes.backend.inprocess.Backend(self.mangler)
                logger.info("using dict cache backend")

    @property
    def _backend(self):
        if not current_app:
            raise RuntimeError("You can only use cache within app context.")
        self.init_app(current_app)
        return current_app.extensions["superdesk_cache"]

    def lock(self, key):
        return self._backend.lock(key)

    def save(self, mapping, *, ttl=None):
        return self._backend.save(mapping, ttl=ttl)

    def load(self, keys):
        val = self._backend.load(keys)
        return val

    def remove(self, keys):
        return self._backend.remove(keys)

    def clean(self):
        return self._backend.clean()


cache_backend = SuperdeskCacheBackend(SuperdeskMangler())
cache = hermes.Hermes(cache_backend, mangler=cache_backend.mangler, ttl=600)
