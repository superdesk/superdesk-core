import sys

from elasticapm.contrib.flask import ElasticAPM


def setup_apm(app, name="Superdesk"):
    in_celery = sys.argv and "worker" in sys.argv
    if getattr(app, "apm", None) is None and app.config.get("APM_SERVER_URL") and app.config.get("APM_SECRET_TOKEN"):
        app.config["ELASTIC_APM"] = {
            "SERVER_URL": app.config["APM_SERVER_URL"],
            "SECRET_TOKEN": app.config["APM_SECRET_TOKEN"],
            "TRANSACTIONS_IGNORE_PATTERNS": ["^OPTIONS "],
            "SERVICE_NAME": "{name} {service}".format(
                name=name,
                service="Celery" if in_celery else "Web",
            ),
        }

        app.apm = ElasticAPM(app)
