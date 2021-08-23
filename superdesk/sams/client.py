from typing import Optional
from flask import current_app
from eve.flaskapp import Eve
from sams_client import SamsClient

_client: SamsClient = None


def get_sams_client(app: Optional[Eve] = None) -> SamsClient:
    global _client

    if not _client:
        if app is None:
            app = current_app

        _client = SamsClient(
            {
                "HOST": app.config.get("SAMS_HOST"),
                "PORT": app.config.get("SAMS_PORT"),
            }
        )

    return _client
