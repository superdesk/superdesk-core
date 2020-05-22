# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013-2019 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import logging
import os
import shutil
import subprocess
import tempfile
import json
from urllib.parse import urljoin
import requests
from os.path import abspath, expanduser
from superdesk.errors import SuperdeskApiError
from superdesk.text_checkers.spellcheckers import CAP_SPELLING, CAP_GRAMMAR
from superdesk.text_checkers.spellcheckers.base import SpellcheckerBase

logger = logging.getLogger(__name__)

PATH_CHECK = "gc_text/fr"
PATH_SUGGEST = "suggest/fr"
# We have an option to select CLI or the HTTP Server, because each options has pros/cons:
# - CLI expects the text to be saved in a file each time
# - Server can't handle spelling suggestion for now
# Grammalecte author has been contacted, and we'll see which options suits the best to
# Superdesk, and if we can contribute to add missing features.
OPT_URL = "GRAMMALECTE_URL"
OPT_CLI = "GRAMMALECTE_CLI"

#: dictionary
OPT_CONFIG = "GRAMMALECTE_CONFIG"
OPT_CONFIG_IGNORE_RULES = "ignore_rules"

# debug flag to activate spelling suggestion when doing a whole text check
# this is resource consuming and getSuggestions should be used instead.
# This flag should be removed at some point. Note that it's only working with CLI
SPELLING_SUGGESTIONS = False


class Grammalecte(SpellcheckerBase):
    """Grammelecte grammar/spelling/style checker integration

    This class works with either the Grammalecte CLI or the Grammalecte server (both are
    downloadable at https://grammalecte.net).
    We use the CLI in priority because it handles spelling suggestions,
    which is not the case with the server.

    The GRAMMELECTE_CLI setting (or environment variable) can be set to
    ``grammelecte-cli.py`` path.

    The GRAMMALECTE_URL setting (or environment variable) can be set to the base URL of
    the server.
    e.g.: if you run Grammelect server with ``grammalecte-server.py -t -p 9999``, you'll
    have to put in the settings ``GRAMMALECTE_URL = http://localhost:9999`` (or use the
    environment variable of the same name).

    If GRAMMALECTE_CLI or GRAMMALECTE_URL are specified, they are used (if both are
    specified, only GRAMMALECTE_CLI will be used). If none is specified, the CLI is search
    in executables path, and if not found default URL (http://localhost:8080) will be used
    .

    Grammelecte behaviour can be specified using GRAMMALECTE_CONFIG setting, which must be
    a dictionary mapping grammalecte option names to their boolean value.
    Check ``grammalecte-cli.py -lo`` to get option names.

    In this dictionary, a special ``ignore_rules`` key can be set to a list of
    rules ids to ignore.
    Check ``grammalecte-cli.py -lr`` to get rules ids.
    """

    name = "grammalecte"
    capacities = (CAP_SPELLING, CAP_GRAMMAR)
    languages = ['fr']

    def __init__(self, app):
        super().__init__(app)

        self._grammalecte_config = None
        self._ignore_rules = None

        # we have two ways to use Grammalecte: CLI and server
        # we use CLI in priority because it handles suggestions for spelling.
        conf_cli_path = self.config.get(OPT_CLI, os.environ.get(OPT_CLI))

        if conf_cli_path is not None:
            # grammalecte_cli.py path is specified, we use CLI
            self.use_cli = True
            self._cli = abspath(expanduser(conf_cli_path))
            return

        conf_base_url = self.config.get(OPT_URL, os.environ.get(OPT_URL))
        if conf_base_url is not None:
            # grammalecte server URL is specified, we use server
            self.base_url = conf_base_url
            self.use_cli = False
            return

        # nothing specified, we try to find the grammalecte_cli.py path, else we use server with default URL

        self._cli = shutil.which("grammalecte-cli.py")
        if self._cli is None:
            # no CLI found, we'll use default URL
            self.use_cli = False
            self.base_url = "http://localhost:8080"
            return
        else:
            self.use_cli = True

    @property
    def grammalecte_config(self):
        """Retrieve Grammalecte config from settings.py or environment variables

        config is cached once retrieved
        """
        if self._grammalecte_config is None:
            config = self.config.get(OPT_CONFIG, {})
            try:
                env_config = json.loads(os.environ[OPT_CONFIG])
            except (KeyError, json.JSONDecodeError):
                env_config = {}
            if not isinstance(config, dict) or not isinstance(env_config, dict):
                logger.warning("Invalid type for Grammalecte configuration, must be a dictionary")
                self._grammalecte_config = {}
                self._ignore_rules = []
                return
            config.update(env_config)
            ignore_rules = config.pop(OPT_CONFIG_IGNORE_RULES, [])
            if not all({isinstance(v, bool) for v in config.values()}):
                logger.warning("Invalid values for Grammalecte configuration, boolean must be used")
                self._grammalecte_config = {}
                self._ignore_rules = []
                return
            if not isinstance(ignore_rules, (list, set)):
                logger.warning('Invalid values for Grammalecte configuration, "ignore_rules" must be a list or a set')
                ignore_rules = []
            self._grammalecte_config = config
            self._ignore_rules = ignore_rules

        return self._grammalecte_config

    def grammalecte2superdesk(self, text, json_data):
        """Convert Grammalecte JSON to format used by Superdesk

        :param str text: original text being checked
        :param dict json_data: json return by Grammalecte
        :return dict: json used by Superdesk
        """
        corrections_data = json_data['data']
        err_list = []
        check_data = {'errors': err_list}

        for corr_data in corrections_data:
            paragraph_idx = corr_data.get('iParagraph', 1) - 1
            start_p_index = 0
            for idx in range(paragraph_idx):
                start_p_index = text.index('\n', start_p_index + 1)
            if paragraph_idx:
                # we must add the line feed character
                start_p_index += 1

            grammar_errors = corr_data.get("lGrammarErrors", [])
            spelling_errors = corr_data.get("lSpellingErrors", [])
            for errors, error_type in ((grammar_errors, 'grammar'),
                                       (spelling_errors, 'spelling')):
                for error in errors:
                    if error.get('sRuleId') in self._ignore_rules:
                        continue
                    start = start_p_index + error['nStart']
                    end = start_p_index + error['nEnd']
                    ercorr_data = {
                        'startOffset': start,
                        'text': text[start:end],
                        'type': error_type,
                    }

                    if 'aSuggestions' in error:
                        ercorr_data['suggestions'] = [{'text': s} for s in error['aSuggestions']]

                    try:
                        ercorr_data['message'] = error['sMessage']
                    except KeyError:
                        pass

                    err_list.append(ercorr_data)

        return check_data

    def _check_cli(self, text):
        with tempfile.NamedTemporaryFile() as f:
            f.write(text.encode('utf-8'))
            f.flush()
            extra_args = []
            if SPELLING_SUGGESTIONS:
                extra_args.append('--with_spell_sugg')
            for opt, activate in self.grammalecte_config.items():
                if activate:
                    extra_args.extend(['-on', opt])
                else:
                    extra_args.extend(['-off', opt])
            cmp_proc = subprocess.run(['/usr/bin/env', 'python3', self._cli,
                                       '--file', f.name, '--json'] + extra_args,
                                      stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE,
                                      check=True)

            out = cmp_proc.stdout.decode('utf-8')
            return self.grammalecte2superdesk(text, json.loads(out))

    def _check_server(self, text):
        check_url = urljoin(self.base_url, PATH_CHECK)
        r = requests.post(check_url, data={"text": text,
                                           "options": json.dumps(self.grammalecte_config)}, timeout=self.CHECK_TIMEOUT)
        if r.status_code != 200:
            raise SuperdeskApiError.internalError("Unexpected return code from Grammalecte")
        return self.grammalecte2superdesk(text, r.json())

    def check(self, text, language=None):
        return self._check_cli(text) if self.use_cli else self._check_server(text)

    def _suggest_cli(self, text):
        cmp_proc = subprocess.run(['/usr/bin/env', 'python3', self._cli,
                                   '--suggest', text, '--json'],
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE,
                                  check=True)

        out = cmp_proc.stdout.decode('utf-8')
        suggestions = json.loads(out).get('aSuggestions', [])
        return {'suggestions': self.list2suggestions(suggestions)}

    def _suggest_server(self, text):
        if self.version_tuple < (1, 2):
            logger.warning("Suggestions not available with this server version")
            return {'suggestions': []}
        check_url = urljoin(self.base_url, PATH_SUGGEST)
        r = requests.post(check_url, data={"token": text}, timeout=self.SUGGEST_TIMEOUT)
        if r.status_code != 200:
            raise SuperdeskApiError.internalError("Unexpected return code from Grammalecte")

        suggestions = r.json().get('suggestions', [])
        return {'suggestions': self.list2suggestions(suggestions)}

    def suggest(self, text, language=None):
        return self._suggest_cli(text) if self.use_cli else self._suggest_server(text)

    def _available_cli(self):
        """Check if grammalecte-cli is available, and parse version"""
        if self._cli is None:
            logger.warning("can't find grammalecte-cli.py in path, can't use Grammalecte.")
            return False
        try:
            with tempfile.NamedTemporaryFile() as f:
                # we use empty file to get version, else grammalecte-cli will wait for input
                # (there is no --version option at the time of writing)
                cmp_proc = subprocess.run([self._cli, '--file', f.name],
                                          stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE,
                                          check=True)

                out = cmp_proc.stdout.decode('utf-8')
                version = out.strip().split()[1][1:]
        except Exception as e:
            logger.warning("can't use Grammalecte: {e}".format(e=e))
            return False

        logger.info("Grammalecte v{version} detected (CLI)".format(version=version))
        self.version = version
        return True

    def _available_server(self):
        """Check if grammalecte-server is launched at expected URL, and retrieve Grammalecte version"""
        check_url = urljoin(self.base_url, PATH_CHECK)
        try:
            r = requests.post(check_url, data={"text": ""}, timeout=self.CHECK_TIMEOUT)
        except Exception as e:
            logger.warning(
                "can't request Grammalecte URL ({check_url}): {e}".
                format(check_url=check_url, e=e))
            return False
        if r.status_code != 200:
            logger.warning(
                "Grammalecte URL ({check_url}) is not returning the expected status"
                .format(check_url=check_url))
            return False

        data = r.json()
        if data['program'] != 'grammalecte-fr':
            logger.warning("unexpected program: {program}".format(program=data['program']))
            return False
        version = data['version']
        logger.info("Grammalecte v{version} detected (server)".format(version=version))
        self.version_tuple = tuple(int(n) for n in version.split('.'))
        if self.version_tuple < (1, 2):
            logger.warning("Suggestions are only available with server version >= 1.2")
        self.version = version
        return True

    def available(self):
        try:
            return self._available_cli() if self.use_cli else self._available_server()
        except Exception as e:
            logger.warning("Can't check Grammalecte availability: {e}".format(e=e))
            return False
