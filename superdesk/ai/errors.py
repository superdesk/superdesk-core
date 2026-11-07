import enum
import logging

from quart_babel import gettext

from superdesk.errors import SuperdeskApiError

logger = logging.getLogger(__name__)


class AIErrorKind(str, enum.Enum):
    """Reason an AI provider request failed, used to pick the HTTP status to answer with"""

    AUTH = "auth"
    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    UPSTREAM = "upstream"
    INVALID_RESPONSE = "invalid_response"


class AIApiError(SuperdeskApiError):
    """An AI request that failed, answered with the kind of failure next to the message

    ``error_kind`` is meant for the client to word its own message on, so the wording shown to an
    editor does not depend on what the server happens to say.
    """

    def __init__(self, status_code: int, message: str, error_kind: str) -> None:
        super().__init__(message=message, status_code=status_code)
        self.error_kind = error_kind

    def to_dict(self) -> dict:
        return {**super().to_dict(), "error_kind": self.error_kind}


class NotSupportedError(SuperdeskApiError):
    """Raised when a request is valid but asks for something this version does not implement.

    Answered with a 400 rather than a 501: the stored configuration allows the request, so the
    client has to change what it asks for, and retrying the same request will not start working.
    """

    def __init__(self, message: str) -> None:
        super().__init__(status_code=400, message=message)


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


def to_api_error(error: AIProviderError, for_administrator: bool = False) -> AIApiError:
    """Convert a provider failure into the HTTP error to answer the client with

    The message is written for an editor unless ``for_administrator`` is set. The provider's own
    detail, the HTTP status it answered with for instance, means nothing to an editor, so it is
    logged for the administrator instead, and only returned on the routes administrators use to
    set a provider up.

    An ``auth`` failure is answered with a gateway error rather than a 401 or 403: the request
    itself was authenticated, it is the stored provider credentials that an administrator has to
    fix, and a 401 would send the client to the login screen.
    """

    logger.warning("AI provider request failed (%s): %s", error.kind.value, error.message)

    if error.kind == AIErrorKind.RATE_LIMIT:
        status_code = 429
        message = gettext("The AI service is busy. Try again in a minute.")
    elif error.kind == AIErrorKind.TIMEOUT:
        status_code = 504
        message = gettext("The AI service took too long to answer. Try again later.")
    elif error.kind == AIErrorKind.AUTH:
        status_code = 502
        message = gettext("The AI service is not set up correctly. Ask an administrator to check it.")
    elif error.kind == AIErrorKind.INVALID_RESPONSE:
        status_code = 502
        message = gettext("The AI service answered with something that could not be read. Try again.")
    else:
        status_code = 502
        message = gettext("The AI service could not be reached. Try again later.")

    return AIApiError(status_code, error.message if for_administrator else message, error.kind.value)
