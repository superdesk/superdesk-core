import enum

from quart_babel import gettext

from superdesk.errors import SuperdeskApiError


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


def to_api_error(error: AIProviderError) -> SuperdeskApiError:
    """Convert a provider failure into the HTTP error to answer the client with

    An ``auth`` failure is answered with a gateway error rather than a 401 or 403: the request
    itself was authenticated, it is the stored provider credentials that an administrator has to
    fix, and a 401 would send the client to the login screen.
    """

    if error.kind == AIErrorKind.RATE_LIMIT:
        return SuperdeskApiError(status_code=429, message=error.message)
    elif error.kind == AIErrorKind.TIMEOUT:
        return SuperdeskApiError(status_code=504, message=error.message)
    elif error.kind == AIErrorKind.AUTH:
        return SuperdeskApiError(
            status_code=502,
            message=gettext("The AI provider rejected the configured credentials"),
        )

    return SuperdeskApiError(status_code=502, message=error.message)
