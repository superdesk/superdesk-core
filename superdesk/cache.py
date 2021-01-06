import redis
import hermes
import hermes.backend
import hermes.backend.dict
import hermes.backend.redis

from flask import current_app as app
from superdesk import json_utils
from superdesk.logging import logger


class SuperdeskRedisBackend(hermes.backend.redis.Backend):
    """Updated init to create redis from URL instead of parsing params."""

    def __init__(self, mangler, **kwargs):
        self.mangler = mangler
        self.client = redis.StrictRedis.from_url(kwargs.pop("url"))
        self._options = kwargs


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

    @property
    def _backend(self):
        if not app:
            raise RuntimeError("You can only use cache within app context.")

        if not app.cache:
            cache_url = app.config.get("CACHE_URL", "")
            if "redis" in cache_url or "unix" in cache_url:
                app.cache = SuperdeskRedisBackend(self.mangler, url=cache_url)
                logger.info("using redis cache backend")
            elif cache_url:
                import hermes.backend.memcached

                app.cache = hermes.backend.memcached.Backend(self.mangler, servers=[cache_url])
                logger.info("using memcached cache backend")
            else:
                app.cache = hermes.backend.dict.Backend(self.mangler)
                logger.info("using dict cache backend")

        return app.cache

    def lock(self, key):
        return self._backend.lock(key)

    def save(self, key=None, value=None, mapping=None, ttl=None):
        return self._backend.save(key, value, mapping, ttl)

    def load(self, keys):
        val = self._backend.load(keys)
        return val

    def remove(self, keys):
        return self._backend.remove(keys)

    def clean(self):
        return self._backend.clean()


cache = hermes.Hermes(SuperdeskCacheBackend, SuperdeskMangler, ttl=600)
