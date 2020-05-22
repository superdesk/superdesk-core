# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013-2019 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import os
import logging
import requests
from superdesk.errors import SuperdeskApiError
from superdesk.text_checkers.spellcheckers import CAP_SPELLING
from superdesk.text_checkers.spellcheckers.base import SpellcheckerBase

logger = logging.getLogger(__name__)
OPT_API_KEY = "LEUVEN_DUTCH_API_KEY"
API_URL = "https://dev.schrijfhulp.be/v1/{method}/"
START_MARKER = "##__ERR_START__##"
END_MARKER = "##__ERR_END__##"


class LeuvenDutch(SpellcheckerBase):
    """University of Leuven Dutch grammar/spellchecker integration

    The LEUVEN_DUTCH_API_KEY setting (or environment variable) must be set to the API key
    """

    name = "leuven_dutch"
    label = "University of Leuven Dutch spellchecker"
    capacities = [CAP_SPELLING]
    languages = ['nl']

    def __init__(self, app):
        super().__init__(app)
        self.api_key = self.config.get(OPT_API_KEY, os.environ.get(OPT_API_KEY))

    def check(self, text, language=None):
        check_url = API_URL.format(method="spellingchecker")
        data = {
            "key": self.api_key,
            "input": text,
            "startmarker": START_MARKER,
            "endmarker": END_MARKER,
        }
        r = requests.post(check_url, data=data, timeout=self.CHECK_TIMEOUT)
        if r.status_code != 200:
            raise SuperdeskApiError.internalError("Unexpected return code from {}".format(self.name))

        data = r.json()

        err_list = []
        check_data = {'errors': err_list}
        len_end_marker = len(END_MARKER)
        output = data['spellingchecker']['output']
        marked = output['marked'].split(START_MARKER)
        # the first item in "marked" is unmarked text, we start our index there
        text_idx = len(marked.pop(0))

        for marked_part in marked:
            mistake = marked_part[:marked_part.find(END_MARKER)]
            ercorr_data = {
                'startOffset': text_idx,
                'text': mistake,
                'type': "spelling",
            }
            err_list.append(ercorr_data)
            text_idx += len(marked_part) - len_end_marker

        return check_data

    def suggest(self, text, language=None):
        check_url = API_URL.format(method="suggesties")
        data = {
            "key": self.api_key,
            "input": text,
        }
        r = requests.post(check_url, data=data, timeout=self.SUGGEST_TIMEOUT)
        if r.status_code != 200:
            raise SuperdeskApiError.internalError("Unexpected return code from {}".format(self.name))
        return {'suggestions': self.list2suggestions(r.json()['suggesties']['output'].get('suggesties', []))}

    def available(self):
        if not self.api_key:
            logger.warning("API key is not set for {label}, please set {opt} variable to use it"
                           .format(label=self.label, opt=OPT_API_KEY))
            return False
        return True
