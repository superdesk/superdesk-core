# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import click

from superdesk.core import get_config, get_current_app, json
from superdesk import get_resource_service
from superdesk.commands import cli
from superdesk.errors import ProviderError


@cli.command("ingest:provider")
@click.option("--provider", "-p", required=True)
async def cli_add_provider(provider: str):
    """Add ingest provider.

    Example:
    ::

        $ python manage.py ingest:provider --provider='{"update_schedule" : { "minutes" : 5, "seconds" : 0 },
            "idle_time" : { "hours" : 0, "minutes" : 0 }, "content_expiry" : 2880, "name" : "aap-demo",
             "source" : "aap-demo", "feeding_service" : "rss",
             "config" : { "url" : "https://abcnews.go.com/abcnews/primetimeheadlines", "field_aliases" : [ ] },
             "feed_parser" : null, "content_types" : [ "text" ]}'

    """

    data = {}
    try:
        data = json.loads(provider)
        data.setdefault("content_expiry", get_config(int, "INGEST_EXPIRY_MINUTES"))

        app = get_current_app()
        validator = app.validator(get_config(dict, "DOMAIN")["ingest_providers"]["schema"], "ingest_providers")
        validation = validator.validate(data)

        if validation:
            await get_resource_service("ingest_providers").post_async([data])
            return data
        else:
            ex = Exception(
                "Failed to add Provider as the data provided is invalid. Errors: {}".format(str(validator.errors))
            )
            raise await ProviderError.providerAddError(exception=ex, provider=data).send_notifications()
    except Exception as ex:
        raise await ProviderError.providerAddError(ex, data).send_notifications()
