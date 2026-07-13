# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from typing import List
import socket
import asyncio
import logging

import imaplib
import aioimaplib

from quart_babel import lazy_gettext as l_

from superdesk.core import get_config
from superdesk.errors import IngestEmailError
from superdesk.io.registry import register_feeding_service, register_feeding_service_parser
from superdesk.io.feeding_services import FeedingService
from superdesk.upload import url_for_media


logger = logging.getLogger(__name__)


class EmailFeedingService(FeedingService):
    """
    Feeding Service class which can read the article(s) from a configured mail box.
    """

    NAME = "email"

    ERRORS = [
        IngestEmailError.emailError().get_error_description(),
        IngestEmailError.emailLoginError().get_error_description(),
    ]

    label = "Email"

    fields = [
        {
            "id": "server",
            "type": "text",
            "label": l_("Email Server"),
            "placeholder": "Email Server",
            "required": True,
            "errors": {6003: "Server not found.", 6002: "Unexpected server response"},
        },
        {
            "id": "port",
            "type": "text",
            "label": l_("Email Server Port"),
            "placeholder": "Email Server Port",
            "required": True,
            "default": "993",
        },
        {"id": "user", "type": "text", "label": l_("User"), "placeholder": "User", "required": True},
        {
            "id": "password",
            "type": "password",
            "label": l_("Password"),
            "placeholder": "Password",
            "required": True,
            "errors": {6000: "Authentication error."},
        },
        {
            "id": "mailbox",
            "type": "text",
            "label": l_("Mailbox"),
            "placeholder": "Mailbox",
            "required": True,
            "errors": {6004: "Authentication error."},
        },
        {"id": "formatted", "type": "boolean", "label": l_("Formatted Email Parser"), "required": True},
        {"id": "filter", "type": "text", "label": l_("Filter"), "placeholder": "Filter", "required": False},
    ]

    async def _test(self, provider):
        await self._update(provider, update=None, test=True)

    async def connect(self, provider: dict, host: str, port: int = aioimaplib.IMAP4_SSL_PORT) -> aioimaplib.IMAP4_SSL:
        try:
            imap = aioimaplib.IMAP4_SSL(host=host, port=port, timeout=get_config(float, "EMAIL_TIMEOUT", 10.0))
            await imap.wait_hello_from_server()
            return imap
        except (socket.gaierror, OSError, asyncio.TimeoutError) as e:
            raise await IngestEmailError.emailHostError(exception=e, provider=provider).send_notifications()
        except asyncio.CancelledError:
            logger.exception("Email Asyncio Task Cancelled")
            raise

    async def authenticate(self, provider: dict, config: dict) -> aioimaplib.IMAP4_SSL:
        server = config.get("server", "")
        port = int(config.get("port", 993))
        imap = await self.connect(provider, server, port)

        try:
            status, lines = await imap.login(config.get("user", ""), config.get("password", ""))
            normalized_status = str(status).upper()
            if normalized_status != "OK":
                response_lines = ". ".join([str(line) for line in lines])
                raise aioimaplib.AioImapException(f"{normalized_status}: {response_lines}")
        except aioimaplib.AioImapException as error:
            raise await IngestEmailError.emailLoginError(error, provider).send_notifications()

        return imap

    async def parse_extra(self, imap: aioimaplib.IMAP4_SSL, num: str, parsed_items: List[dict]) -> None:
        """Parse extra metadata

        This method is called after main parsing, and can be used by subclasses
        """
        pass

    async def _update(self, provider, update, test=False):
        config = provider.get("config", {})
        new_items = []

        try:
            imap = await self.authenticate(provider, config)

            try:
                rv, data = await imap.select(config.get("mailbox", None))
                if str(rv).upper() != "OK":
                    raise await IngestEmailError.emailMailboxError().send_notifications()
                try:
                    # at least one criterion must be set
                    # (see file:///usr/share/doc/python/html/library/imaplib.html#imaplib.IMAP4.search)
                    rv, data = await imap.search(config.get("filter") or "(UNSEEN)")
                    if str(rv).upper() != "OK":
                        raise await IngestEmailError.emailFilterError().send_notifications()
                    for num in data[0].split():
                        rv, data = await imap.fetch(num, "(RFC822)")
                        if str(rv).upper() == "OK" and not test:
                            try:
                                parser = await self.get_feed_parser(provider, data)
                                parsed_items = await parser.parse(data, provider)
                                await self.parse_extra(imap, num, parsed_items)
                                new_items.append(parsed_items)
                                rv, data = await imap.store(num, "+FLAGS", "\\Seen")
                                if str(rv).upper() != "OK":
                                    logger.warning("Failed to mark email as read", extra=dict(status=rv, lines=data))
                            except IngestEmailError:
                                logger.error("Failed to parse email", extra=dict(status=rv, data=data))
                                continue
                finally:
                    await imap.close()
            finally:
                await imap.logout()
        except IngestEmailError as ex:
            raise await ex.send_notifications()
        except Exception as ex:
            raise await IngestEmailError.emailError(ex, provider).send_notifications()
        return new_items

    def prepare_href(self, href, mimetype=None):
        return url_for_media(href, mimetype)


register_feeding_service(EmailFeedingService)
register_feeding_service_parser(EmailFeedingService.NAME, "email_rfc822")
