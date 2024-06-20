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
import json
from superdesk.errors import SuperdeskApiError
from superdesk.text_checkers.spellcheckers import CAP_SPELLING, CAP_GRAMMAR, LANG_ANY
from superdesk.text_checkers.spellcheckers.base import SpellcheckerBase

logger = logging.getLogger(__name__)
API_URL = "LANGUAGETOOL_API_URL"
OPT_API_KEY = "LANGUAGETOOL_API_KEY"
OPT_CONFIG = "LANGUAGETOOL_CONFIG"


class Languagetool(SpellcheckerBase):
    """Languagetool grammar/spellchecker integration

    The LANGUAGETOOL_API_URL setting (or environment variable) must be set
    """

    name = "languagetool"
    label = "Languagetool spellchecker"
    capacities = (CAP_SPELLING, CAP_GRAMMAR)
    languages = [LANG_ANY]

    def __init__(self, app):
        super().__init__(app)
        self.api_url = self.config.get(API_URL, os.environ.get(API_URL))
        self.api_config = None

    @property
    def languagetool_config(self):
        """Retrieve Languagetool config from settings.py or environment variables

        config is cached once retrieved
        """
        if self.api_config is None:
            opt_config = self.config.get(OPT_CONFIG, {})
            api_key = self.config.get(OPT_API_KEY, os.environ.get(OPT_API_KEY))
            if api_key:
                opt_config['apiKey'] = api_key
            try:
                env_config = json.loads(os.environ[OPT_CONFIG])
            except (KeyError, json.JSONDecodeError):
                env_config = {}
            if not isinstance(opt_config, dict) or not isinstance(env_config, dict):
                logger.warning("Invalid type for {label} configuration, must be a dictionary".format(label=self.label))
                self.api_config = {}
                return self.api_config
            opt_config.update(env_config)
            self.api_config = opt_config

        return self.api_config

    def check(self, text, language=None):
        payload = {
            'text': text,
            'language': language,
        }

        # Add apiKey and additional options from the environment variable
        additional_options = self.languagetool_config()
        payload.update(additional_options)

        try:
            # Send the POST request to the LanguageTool API
            response = requests.post(self.api_url, data=payload)
            response.raise_for_status()
            response_data = response.json()
        except (requests.RequestException, json.JSONDecodeError) as e:
            raise SuperdeskApiError.internalError(
                "Unexpected error from {label}: {e}".format(
                    label=self.label, e=str(e)
                ), exception=e
            )

        # Initialize an empty list to store errors
        err_list = []

        # Iterate over the matches in the response
        matches = response_data.get('matches', [])
        if not isinstance(matches, list):
            logger.warning("Unexpected {label} response format: 'matches' should be a list.".format(label=self.label))
            return {"errors": []}

        for match in matches:
            issue_type = match.get('rule', {}).get('issueType')
            if issue_type in ['misspelling', 'whitespace', 'other']:
                error_type = 'spelling'
            elif issue_type in ['grammar', 'characters', 'typographical', 'locale-violation']:
                error_type = 'grammar'
            else:
                continue

            error = {
                "message": match.get('message', ''),
                "startOffset": match.get('offset', -1),
                "suggestions": [{"text": replacement.get('value', '')} for replacement in match.get('replacements', [])],
                "text": text[match.get('offset', 0):match.get('offset', 0) + match.get('length', 0)],
                "type": error_type,
            }
            err_list.append(error)

        check_data = {"errors": err_list}
        return check_data

    def suggest(self, text, language=None):
        payload = {
            'text': text,
            'language': language,
        }

        # Add apiKey and additional options from the environment variable
        additional_options = self.languagetool_config()
        payload.update(additional_options)

        try:
            # Send the POST request to the LanguageTool API
            response = requests.post(self.api_url, data=payload)
            response.raise_for_status()
            response_data = response.json()
        except (requests.RequestException, json.JSONDecodeError) as e:
            raise SuperdeskApiError.internalError(
                "Unexpected error from {label}: {e}".format(label=self.label, e=str(e)), exception=e)

        # Initialize an empty list to store all replacement suggestions
        replacements = []

        matches = response_data.get('matches', [])
        if not isinstance(matches, list):
            logger.warning("Unexpected {label} response format: 'matches' should be a list.".format(label=self.label))
            return []

        for match in matches:
            issue_type = match.get('rule', {}).get('issueType')
            if issue_type in ['misspelling', 'whitespace', 'other', 'grammar', 'characters', 'typographical', 'locale-violation']:
                for replacement in match.get('replacements', []):
                    replacements.append(replacement.get('value', ''))

        return {"suggestions": self.list2suggestions(replacements)}

    def available(self):
        if not self.api_url:
            logger.warning(
                "API url is not set for {label}, please set {opt} variable to use it".format(
                    label=self.label, opt=API_URL
                )
            )
            return False

        payload = {
            'text': 'test',
            'language': 'auto',
        }
        additional_options = self.languagetool_config()
        payload.update(additional_options)

        try:
            # Send the POST request to the LanguageTool API
            response = requests.post(self.api_url, data=payload)
            response.raise_for_status()
        except (requests.RequestException, json.JSONDecodeError) as e:
            logger.warning(
                "can't request {label} URL ({url}): {e}".format(label=self.label, url=self.api_url, e=str(e))
            )
            return False
        if response.status_code != 200:
            logger.warning(
                "{label} URL ({url}) is not returning the expected status".format(label=self.label, url=self.api_url)
            )
            return False
        return True


def init_app(app):
    Languagetool(app)
