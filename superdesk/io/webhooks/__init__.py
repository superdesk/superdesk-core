# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013 - 2017 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk.resource import Resource
from superdesk.eve_async import AsyncBaseService
from superdesk.io.commands import update_ingest
import os
from superdesk import get_resource_service
from superdesk.flask import request, abort
import logging

logger = logging.getLogger(__name__)


class FeedingServiceWebhookAuth(object):
    def authenticate(self):
        abort(403, description="You are not authorized to access this resource")

    def authorized(self, allowed_roles, resource, method):
        try:
            # provider's id may be used in the future
            provider_name = request.args["provider_name"]
        except KeyError:
            logger.warning("Got an invalid webhook request (missing provider name) ")
            return False
        # FIXME: there can be a conflict if 2 provider names are similar but with different case
        #        this will be fixed when we'll use id instead of name
        env_name = "WEBHOOK_{}_AUTH".format(provider_name.upper())
        try:
            auth_key = os.environ[env_name]
        except KeyError:
            logger.error("{} environment variable is not set".format(env_name))
            return False
        return request.args.get("auth") == auth_key


class FeedingServiceWebhookResource(Resource):
    resource_methods = ["POST"]
    authentication = FeedingServiceWebhookAuth
    # we don't want schema validation to accept any webhook data
    allow_unknown = True


class FeedingServiceWebhookService(AsyncBaseService):
    """Service giving metadata on backend itself"""

    async def create_async(self, docs, **kwargs):
        # we don't want to create anything
        # we just use this service to trigger the provider
        # and return a fake id
        await self.trigger_provider()
        return [0]

    async def trigger_provider(self):
        provider_name = request.args["provider_name"]
        lookup = {"name": provider_name}
        async for provider in await get_resource_service("ingest_providers").get_async(req=None, lookup=lookup):
            kwargs = {
                "provider": provider,
                "rule_set": await update_ingest.get_provider_rule_set(provider),
                "routing_scheme": await update_ingest.get_provider_routing_scheme(provider),
            }
            await update_ingest.update_provider.apply_async(expires=update_ingest.get_task_ttl(provider), kwargs=kwargs)


def init_app(app) -> None:
    service = FeedingServiceWebhookService()
    FeedingServiceWebhookResource("webhook", app=app, service=service)
