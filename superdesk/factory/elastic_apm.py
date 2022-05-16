import re
import flask

from typing import Literal
from elasticapm.contrib.flask import ElasticAPM


def setup_apm(app: flask.Flask, service="Core API") -> None:
    if getattr(app, "apm", None) is None and app.config.get("APM_SERVER_URL") and app.config.get("APM_SECRET_TOKEN"):
        app.config["ELASTIC_APM"] = {
            "DEBUG": app.debug,
            "ENVIRONMENT": get_environment(app),
            "SERVER_URL": app.config["APM_SERVER_URL"],
            "SECRET_TOKEN": app.config["APM_SECRET_TOKEN"],
            "TRANSACTIONS_IGNORE_PATTERNS": ["^OPTIONS "],
            "SERVICE_NAME": "{app} - {service}".format(
                app=app.config.get("APM_SERVICE_NAME") or app.config.get("APPLICATION_NAME"), service=service
            ),
        }

        app.apm = ElasticAPM(app)


def get_environment(app: flask.Flask) -> Literal["testing", "staging", "production"]:
    if app.config.get("CLIENT_URL"):
        if "localhost" in app.config["CLIENT_URL"] or app.debug:
            return "testing"
        if re.search(r"-(dev|demo|test|staging)", app.config["CLIENT_URL"]):
            return "staging"
    return "production"
