
import flask
import unittest
import superdesk.tests as tests
import superdesk.auth.saml as saml

from unittest.mock import patch


SAML_DATA = {
    "http://schemas.microsoft.com/identity/claims/tenantid": ["3cd37c1d"],
    "http://schemas.microsoft.com/identity/claims/objectidentifier": ["2f2a99f7"],
    "http://schemas.microsoft.com/identity/claims/displayname": ["Bar, Foo"],
    "http://schemas.microsoft.com/identity/claims/identityprovider": ["https://sts.windows.net/3cd37c1d/"],
    "http://schemas.microsoft.com/claims/authnmethodsreferences": [
        "urn:oasis:names:tc:SAML:2.0:ac:classes:PasswordProtectedTransport",
    ],
    "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname": ["Foo"],
    "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname": ["Bar"],
    "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress": ["foo.bar@example.com"],
    "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name": ["foo"],
    "displayname": ["Bar, Foo"],
    "country": ["CA"],
    "city": ["Toronto"],
    "department": ["IT"]
}


class SamlAuthTestCase(tests.TestCase):

    @patch('superdesk.auth.saml.init_saml_auth')
    def test_create_missing_user(self, init_mock):
        with self.app.test_client() as c:
            flask.session[saml.SESSION_NAME_ID] = 'foo.bar@example.com'
            flask.session[saml.SESSION_USERDATA_KEY] = SAML_DATA

            resp = saml.index()
            self.assertIn('404', resp)

            with patch.dict(self.app.config, {'USER_EXTERNAL_AUTO_CREATE': True}):
                resp = saml.index()
            self.assertNotIn('404', resp)

    @patch('superdesk.auth.saml.init_saml_auth')
    def test_create_missing_user_missing_userdata(self, init_mock):
        with self.app.test_client() as c:
            # with missing data it can't work
            flask.session[saml.SESSION_NAME_ID] = 'foo.bar@example.com'
            flask.session[saml.SESSION_USERDATA_KEY] = SAML_DATA.copy()
            flask.session[saml.SESSION_USERDATA_KEY].update({
                "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name": [],
            })
            with patch.dict(self.app.config, {'USER_EXTERNAL_AUTO_CREATE': True}):
                resp = saml.index()
            self.assertIn('404', resp)

    @patch('superdesk.auth.saml.init_saml_auth')
    def test_handle_saml_name_id_not_email(self, init_mock):
        with self.app.test_client() as c:
            # with missing data it can't work
            flask.session[saml.SESSION_NAME_ID] = 'something_weird_like_guid'
            flask.session[saml.SESSION_USERDATA_KEY] = SAML_DATA.copy()
            with patch.dict(self.app.config, {'USER_EXTERNAL_AUTO_CREATE': True}):
                resp = saml.index()
            self.assertNotIn('404', resp)

    @patch('superdesk.auth.saml.init_saml_auth')
    def test_update_user_data_when_it_changes(self, init_mock):
        with self.app.test_client() as c:
            # with missing data it can't work
            flask.session[saml.SESSION_NAME_ID] = 'nameId'
            flask.session[saml.SESSION_USERDATA_KEY] = SAML_DATA.copy()
            with patch.dict(self.app.config, {'USER_EXTERNAL_AUTO_CREATE': True}):
                resp = saml.index()

            flask.session[saml.SESSION_USERDATA_KEY].update({
                "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname": ["John"],
                "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname": ["Doe"],
                "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress": ["foo.bar@example.com"],
                "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name": ["john"],
                "displayname": ["Doe, John"],
            })

            with patch.dict(self.app.config, {'USER_EXTERNAL_AUTO_CREATE': True}):
                resp = saml.index()

        user = self.app.data.find_one('users', req=None, email='foo.bar@example.com')
        self.assertEqual('John', user['first_name'])
        self.assertEqual('Doe', user['last_name'])
        self.assertEqual('Doe, John', user['display_name'])
