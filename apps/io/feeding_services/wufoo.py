# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk.io.registry import register_feeding_service, register_feeding_service_parser
from superdesk.io.feeding_services import FeedingService
from superdesk.errors import IngestApiError
import requests
import traceback
# from pytz import timezone


WUFOO_URL = 'https://{subdomain}.wufoo.com/api/v3/'
WUFOO_QUERY_FORM = 'forms/{form_hash}/'
WUFOO_QUERY_FIELDS = 'fields.json'
WUFOO_QUERY_ENTRIES = 'entries.json'


class WufooFeedingService(FeedingService):
    """
    Feeding Service class which can read article(s) using Wufoo API
    """

    NAME = 'wufoo'

    ERRORS = [IngestApiError.apiTimeoutError().get_error_description(),
              IngestApiError.apiRedirectError().get_error_description(),
              IngestApiError.apiRequestError().get_error_description(),
              IngestApiError.apiGeneralError().get_error_description()]

    label = 'Wufoo feed API'

    fields = [
        {
            'id': 'wufoo_username', 'type': 'text', 'label': 'Login',
            'placeholder': 'Wufoo login', 'required': True
        },
        {
            'id': 'wufoo_api_key', 'type': 'password', 'label': 'API key',
            'placeholder': 'Wufoo API Key', 'required': True
        }
    ]

    def __init__(self):
        super().__init__()
        self.fields_cache = {}

    def _update(self, provider, update):
        user = provider['config']['wufoo_username']
        wufoo_data = {
            "url": WUFOO_URL.format(subdomain=user),
            "user": user,
            "api_key": provider['config']['wufoo_api_key'],
            "form_query_entries_tpl": WUFOO_QUERY_FORM + WUFOO_QUERY_ENTRIES,
            "update": update}
        try:
            parser = self.get_feed_parser(provider, None)
        except requests.exceptions.Timeout as ex:
            raise IngestApiError.apiTimeoutError(ex, provider)
        except requests.exceptions.TooManyRedirects as ex:
            raise IngestApiError.apiRedirectError(ex, provider)
        except requests.exceptions.RequestException as ex:
            raise IngestApiError.apiRequestError(ex, provider)
        except Exception as error:
            traceback.print_exc()
            raise IngestApiError.apiGeneralError(error, self.provider)
        items = parser.parse(wufoo_data, provider)
        return [items]


register_feeding_service(WufooFeedingService)
register_feeding_service_parser(WufooFeedingService.NAME, 'wufoo')
