
import flask

from flask import request, g
from unittest import TestCase
from content_api.tokens import generate_subscriber_token, decode_subscriber_token, SubscriberTokenAuth


class SubscriberTokenTestCase(TestCase):

    def setUp(self):
        self.app = flask.Flask(__name__)
        self.secret = 'test-secret'
        self.app.config['SECRET_KEY'] = self.secret
        self.subscriber = {'_id': 'foo', 'name': 'bar'}

    def test_generate_token_for_subscriber(self):
        with self.app.app_context():
            token = generate_subscriber_token(self.subscriber)
            decoded = decode_subscriber_token(token)
        self.assertEqual(self.subscriber['_id'], decoded['sub'])

    def test_token_auth(self):
        auth = SubscriberTokenAuth()

        with self.app.test_request_context():
            self.assertFalse(auth.authorized([], None, 'GET'))
            token = generate_subscriber_token(self.subscriber)

        with self.app.test_request_context(headers={'Authorization': b'Bearer ' + token}):
            self.assertTrue(auth.authorized([], None, 'GET'))
            self.assertEqual(self.subscriber['_id'], g.get('user'))
