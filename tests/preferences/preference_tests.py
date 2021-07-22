"""Preference_Tests Class"""
# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from apps.preferences import PreferencesService
from superdesk.tests import TestCase


class PreferenceTests(TestCase):
    """Unit Test Class related to Preference routines.

    :param TestCase: test case to use
    """

    def setUp(self):
        """Setup for test

        :param self: self
        """
        self._default_user_settings = {
            "archive:view": {
                "default": "mgrid",
                "label": "Users archive view format",
                "type": "string",
                "category": "archive",
                "allowed": ["mgrid", "compact"],
                "view": "mgrid",
            },
            "feature:preview": {
                "category": "feature",
                "default": "false",
                "type": "bool",
                "enabled": "false",
                "label": "Andrew",
            },
            "email:notification": {
                "category": "notifications",
                "default": "true",
                "type": "bool",
                "enabled": "true",
                "label": "Send Hello",
            },
        }

        self._default_session_settings = {
            "desk:items": [],
            "stage:items": [],
            "pinned:items": [],
            "scratchpad:items": [],
        }

        self._session_update = {"session_preferences": {"scratchpad:items": [123]}}

        self._user_update = {"user_preferences": {"archive:view": {"label": "Testing user preferences"}}}

    def test_setting_partial_session_preferences_with_empty_existing(self):
        """Test case for setting partial session perferences with empty existing

        :param self: self
        """
        update = self._session_update
        existing_session_settings = {"1234": {}}

        PreferencesService.update_session_prefs(self, update, existing_session_settings, "1234")
        self.assertListEqual(update["session_preferences"]["1234"]["scratchpad:items"], [123])

    def test_setting_partial_session_preferences_with_existing(self):
        """Test case for setting partial session perferences with exiting

        :param self: self
        """
        existing_session_settings = {
            "1234": {"desk:items": [], "stage:items": [], "pinned:items": ["a", "b", "c"], "scratchpad:items": []}
        }

        update = self._session_update
        PreferencesService.update_session_prefs(self, update, existing_session_settings, "1234")
        self.assertListEqual(update["session_preferences"]["1234"]["scratchpad:items"], [123])

    def test_setting_partial_user_preferences_with_existing(self):
        """Test case for setting partial user preferences with existing

        :param self: self
        """
        update = self._user_update
        PreferencesService.update_user_prefs(self, update, {})
        self.assertEqual(update["user_preferences"]["archive:view"]["label"], "Testing user preferences")

    def test_setting_partial_user_preferences_with_empty_existing(self):
        """Test case for setting partial user preferences with empty existing

        :param self: self
        """
        update = self._user_update
        existing_user_settings = {
            "archive:view": {
                "default": "mgrid",
                "label": "Users archive view format",
                "type": "string",
                "category": "archive",
                "allowed": ["mgrid", "compact"],
                "view": "mgrid",
            }
        }

        PreferencesService.update_user_prefs(self, update, existing_user_settings)
        self.assertEqual(update["user_preferences"]["archive:view"]["label"], "Testing user preferences")
