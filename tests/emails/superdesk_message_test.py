import unittest

import flask
import flask_mail
from email.parser import Parser
from email.header import decode_header

from superdesk.emails import SuperdeskMessage


class SuperdeskMessageTestCase(unittest.TestCase):
    subject = 'темы для выделения выделения выделения'

    def test_unicode_subject(self):
        app = flask.Flask(__name__)
        flask_mail.Mail(app)
        with app.app_context():
            msg = SuperdeskMessage(self.subject, sender='root', body='test')
            out = msg.as_bytes()
        parsed = Parser().parsestr(out.decode('utf-8'), headersonly=True)
        decoded, charset = decode_header(parsed['subject'])[0]
        self.assertEqual(self.subject, decoded.decode(charset))
