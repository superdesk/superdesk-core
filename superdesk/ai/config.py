import logging
import os

from superdesk.core.config import ConfigModel

logger = logging.getLogger(__name__)

#: Seconds nginx waits for a proxied response unless ``proxy_read_timeout`` says otherwise
NGINX_DEFAULT_READ_TIMEOUT = 60

#: Default of ``WEB_TIMEOUT``, the Hypercorn ``read_timeout`` of a Superdesk deployment. Hypercorn
#: drops the connection of a request that has not been answered in that time.
WEB_TIMEOUT_DEFAULT = 30


class AIConfig(ConfigModel):
    #: Seconds to wait for a response from an AI provider before the request is aborted
    request_timeout: int = 25

    #: How many AI actions one user may run per minute, ``0`` for no limit
    rate_limit_per_minute: int = 20


#: Populated by the app from the ``AI_`` prefixed settings when ``superdesk.ai`` is loaded.
#: Reading an attribute before the module is loaded raises a ``RuntimeError``.
config = AIConfig()


def check_request_timeout() -> None:
    """Warn when a provider is allowed longer than the server or proxy waits for the request

    When the server or the proxy gives up first, the editor gets a dropped connection or a gateway
    error instead of the timeout message, and the provider is still paid for the run. The proxy
    configuration cannot be read from here, so the nginx default is assumed.
    """

    try:
        web_timeout = int(os.environ.get("WEB_TIMEOUT", WEB_TIMEOUT_DEFAULT))
    except ValueError:
        web_timeout = WEB_TIMEOUT_DEFAULT

    limit = min(web_timeout, NGINX_DEFAULT_READ_TIMEOUT)
    if config.request_timeout >= limit:
        logger.warning(
            "AI_REQUEST_TIMEOUT is %s seconds, which is not below the %s seconds the server or proxy waits for "
            "a request (WEB_TIMEOUT, nginx proxy_read_timeout). Slow AI runs will fail with a dropped "
            "connection instead of a timeout message.",
            config.request_timeout,
            limit,
        )
