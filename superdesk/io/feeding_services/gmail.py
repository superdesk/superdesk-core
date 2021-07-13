# This file is part of Superdesk.
#
# Copyright 2020 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import imaplib
from bson import ObjectId
from os.path import join
import time
import logging
from flask_babel import lazy_gettext as l_
import superdesk
from superdesk.auth import oauth
from superdesk.errors import IngestEmailError
from superdesk.io.registry import register_feeding_service, register_feeding_service_parser
from . import EmailFeedingService


logger = logging.getLogger(__name__)


class GMailFeedingService(EmailFeedingService):
    """
    Feeding Service class which can read the article(s) from a configured mail box.
    """

    NAME = "gmail"

    ERRORS = [
        IngestEmailError.emailError().get_error_description(),
        IngestEmailError.emailLoginError().get_error_description(),
    ]

    label = "Gmail"

    fields = [
        {
            "id": "email",
            "type": "text",
            "label": l_("email"),
            "readonly": True,
            "show_expression": "provider.config['email'] != null",
        },
        {
            "id": "log_in_url",
            "type": "url_request",
            "label": l_("Log-in with GMail"),
            # provider._id != null              provider has to be saved before trying to log in
            # provider.config['email'] == null  do not display log-in button if logged-in already
            "show_expression": "provider._id != null && provider.config['email'] == null",
        },
        {
            "id": "log_out_url",
            "type": "url_request",
            "label": l_("Log-out"),
            # provider.config['email'] != null  only display log-out button if already logged in
            "show_expression": "provider.config['email'] != null",
        },
        {
            "id": "mailbox",
            "type": "text",
            "label": l_("Mailbox"),
            "default_value": "INBOX",
            "placeholder": l_("Mailbox"),
            "required": True,
            "errors": {6004: "Authentication error."},
        },
        {"id": "filter", "type": "text", "label": l_("Filter"), "placeholder": "Filter", "required": False},
    ]

    @classmethod
    def init_app(cls, app):
        # we need to access config to set the URL, so we do it here
        field = next(f for f in cls.fields if f["id"] == "log_in_url")
        field["url"] = join(app.config["SERVER_URL"], "login", "google", "{PROVIDER_ID}")
        field = next(f for f in cls.fields if f["id"] == "log_out_url")
        field["url"] = join(app.config["SERVER_URL"], "logout", "google", "{PROVIDER_ID}")

    def _test(self, provider):
        self._update(provider, update=None, test=True)

    def authenticate(self, provider: dict, config: dict) -> imaplib.IMAP4_SSL:
        oauth2_token_service = superdesk.get_resource_service("oauth2_token")
        token = oauth2_token_service.find_one(req=None, _id=ObjectId(provider["_id"]))
        if token is None:
            raise IngestEmailError.notConfiguredError(ValueError(l_("You need to log in first")), provider=provider)
        imap = imaplib.IMAP4_SSL("imap.gmail.com")

        if token["expires_at"].timestamp() < time.time() + 600:
            logger.info("Refreshing token for {provider_name}".format(provider_name=provider["name"]))
            token = oauth.refresh_google_token(token["_id"])

        auth_string = "user={email}\x01auth=Bearer {token}\x01\x01".format(
            email=token["email"], token=token["access_token"]
        )
        imap.authenticate("XOAUTH2", lambda __: auth_string.encode())
        return imap


register_feeding_service(GMailFeedingService)
register_feeding_service_parser(GMailFeedingService.NAME, "email_rfc822")
