from sams_client import SamsClient
from superdesk.core import get_app_config

_client: SamsClient = None


def get_sams_client() -> SamsClient:
    global _client

    if not _client:
        _client = SamsClient(
            {
                "HOST": get_app_config("SAMS_HOST"),
                "PORT": get_app_config("SAMS_PORT"),
            }
        )

    return _client
