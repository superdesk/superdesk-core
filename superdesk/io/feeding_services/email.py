# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import socket
import imaplib

from flask import current_app as app
from flask_babel import lazy_gettext as l_
from superdesk.errors import IngestEmailError
from superdesk.io.registry import register_feeding_service, register_feeding_service_parser
from superdesk.io.feeding_services import FeedingService
from superdesk.upload import url_for_media


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

    def _test(self, provider):
        self._update(provider, update=None, test=True)

    def authenticate(self, provider: dict, config: dict) -> imaplib.IMAP4_SSL:
        server = config.get("server", "")
        port = int(config.get("port", 993))
        try:
            socket.setdefaulttimeout(app.config.get("EMAIL_TIMEOUT", 10))
            imap = imaplib.IMAP4_SSL(host=server, port=port)
        except (socket.gaierror, OSError) as e:
            raise IngestEmailError.emailHostError(exception=e, provider=provider)

        try:
            imap.login(config.get("user", None), config.get("password", None))
        except imaplib.IMAP4.error:
            raise IngestEmailError.emailLoginError(imaplib.IMAP4.error, provider)

        return imap

    def _update(self, provider, update, test=False):
        config = provider.get("config", {})
        new_items = []

        try:
            imap = self.authenticate(provider, config)

            try:
                rv, data = imap.select(config.get("mailbox", None), readonly=False)
                if rv != "OK":
                    raise IngestEmailError.emailMailboxError()
                try:
                    rv, data = imap.search(None, config.get("filter", "(UNSEEN)"))
                    if rv != "OK":
                        raise IngestEmailError.emailFilterError()
                    for num in data[0].split():
                        rv, data = imap.fetch(num, "(RFC822)")
                        if rv == "OK" and not test:
                            try:
                                parser = self.get_feed_parser(provider, data)
                                new_items.append(parser.parse(data, provider))
                                rv, data = imap.store(num, "+FLAGS", "\\Seen")
                            except IngestEmailError:
                                continue
                finally:
                    imap.close()
            finally:
                imap.logout()
        except IngestEmailError:
            raise
        except Exception as ex:
            raise IngestEmailError.emailError(ex, provider)
        return new_items

    def prepare_href(self, href, mimetype=None):
        return url_for_media(href, mimetype)


register_feeding_service(EmailFeedingService)
register_feeding_service_parser(EmailFeedingService.NAME, "email_rfc822")
