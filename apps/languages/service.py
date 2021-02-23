# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import logging
import superdesk

from superdesk.services import BaseService
from superdesk.utils import ListCursor


logger = logging.getLogger(__name__)


def view_language(item):
    language = item.copy()
    language["_id"] = language["qcode"]
    language["label"] = language["name"]
    language["language"] = language["qcode"]

    # allow translations
    language.setdefault("source", True)
    language.setdefault("destination", True)

    return language


class LanguagesService(BaseService):
    def get(self, req, lookup):
        """
        Return the list of languages defined on config file.
        """
        languages = superdesk.get_resource_service("vocabularies").get_languages()
        return ListCursor([view_language(lang) for lang in languages])
