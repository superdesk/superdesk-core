import enum


class AIErrorKind(str, enum.Enum):
    """Reason an AI provider request failed, used to pick the HTTP status to answer with"""

    AUTH = "auth"
    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    UPSTREAM = "upstream"
    INVALID_RESPONSE = "invalid_response"


class AIProviderError(Exception):
    """Raised by provider clients when a request to the provider does not produce a usable result.

    Messages are built from the request outcome (status code, kind of failure) only. The provider
    credentials and the provider's own response body must never end up in a message, as those
    messages are returned to clients and written to the logs.
    """

    def __init__(self, kind: AIErrorKind, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.kind = kind
        self.message = message
        self.status_code = status_code
