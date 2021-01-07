# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013-2019 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import re
import logging

# from superdesk.errors import SuperdeskApiError
import superdesk
from superdesk.text_checkers.spellcheckers import SPELLCHECKER_DEFAULT, CAP_SPELLING, LANG_ANY
from superdesk.text_checkers.spellcheckers.base import SpellcheckerBase
from superdesk.errors import SuperdeskApiError


logger = logging.getLogger(__name__)


class Default(SpellcheckerBase):
    """Default spellchecker of Superdesk

    This spellchecker works with internal dictionaries, in any language.
    """

    name = SPELLCHECKER_DEFAULT
    label = "Superdesk default spellchecker"
    capacities = (CAP_SPELLING,)
    languages = [LANG_ANY]

    def check(self, text, language=None):
        if language is None:
            raise SuperdeskApiError.badRequestError("missing language for default spellchecker")
        dictionaries_service = superdesk.get_resource_service("dictionaries")
        model = dictionaries_service.get_model_for_lang(language)
        err_list = []
        check_data = {"errors": err_list}
        for match in re.finditer(r"([^\d\W]+-?)+", text):
            word = match.group().lower()
            if word not in model:
                ercorr_data = {
                    "startOffset": match.start(),
                    "text": match.group(),
                    "type": "spelling",
                }
                err_list.append(ercorr_data)
        return check_data

    def suggest(self, text, language=None):
        if language is None:
            raise SuperdeskApiError.badRequestError("missing language for default spellchecker")
        spellcheck_service = superdesk.get_resource_service("spellcheck")
        suggestions = spellcheck_service.suggest(text, language)
        return {"suggestions": self.list2suggestions(suggestions)}
