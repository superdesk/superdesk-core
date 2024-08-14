# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import urllib
import requests

from superdesk.core import get_app_config
from superdesk.errors import SuperdeskApiError
from quart_babel import gettext as _


class AlchemyKeywordsProvider:
    """Keyword provider that user the Alchemy API(http://www.alchemyapi.com/api)"""

    def __init__(self):
        self._http = requests.Session()

    def get_keywords(self, text):
        if not get_app_config("KEYWORDS_KEY_API"):
            raise SuperdeskApiError.notFoundError(_("AlchemyAPI key is not set"))

        params = {"apikey": get_app_config("KEYWORDS_KEY_API"), "outputMode": "json"}

        url = (
            get_app_config("KEYWORDS_BASE_URL")
            + "/text/TextGetRankedNamedEntities"
            + "?"
            + urllib.parse.urlencode(params)
        )

        values = {"text": text}

        result = ""
        try:
            result = self._http.post(url, data=values)
        except Exception as ex:
            raise SuperdeskApiError.internalError(_("Fail to connect to Alchemy service"), exception=ex)

        try:
            keywords = result.json()
            return keywords.get("entities", [])
        except Exception as ex:
            raise SuperdeskApiError.internalError(_("Fail to parse the response from Alchemy service"), exception=ex)
