import re

from typing import Literal
from superdesk.flask import Flask


def setup_apm(app: Flask, service="Core API") -> None:
    # APM is intentionally disabled (see commented-out client initialization below).
    # Keep this function as a no-op to avoid constructing unused ELASTIC_APM config,
    # including SECRET_TOKEN, when no APM client is active.
    return

    # disable apm, doesn't support quart
    #
    # from elasticapm.contrib.flask import ElasticAPM
    # app.apm = ElasticAPM(app)  # type: ignore


def get_environment(app: Flask) -> Literal["testing", "staging", "production"]:
    if app.config.get("CLIENT_URL"):
        if "localhost" in app.config["CLIENT_URL"] or app.debug:
            return "testing"
        if re.search(r"-(dev|demo|test|staging)", app.config["CLIENT_URL"]):
            return "staging"
    return "production"
