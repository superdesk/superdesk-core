from superdesk.core.config import ConfigModel


class AIConfig(ConfigModel):
    #: Seconds to wait for a response from an AI provider before the request is aborted
    request_timeout: int = 60


#: Populated by the app from the ``AI_`` prefixed settings when ``superdesk.ai`` is loaded.
#: Reading an attribute before the module is loaded raises a ``RuntimeError``.
config = AIConfig()
