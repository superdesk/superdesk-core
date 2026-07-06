import unittest
from email.parser import Parser
from email.header import decode_header

from superdesk.core.emails import EmailFactory, EmailMessage
from superdesk.flask import Flask


class SuperdeskMessageTestCase(unittest.TestCase):
    subject = "темы для выделения выделения выделения"

    async def test_unicode_subject(self):
        app = Flask(__name__)
        app.mail = EmailFactory()
        async with app.app_context():
            msg = EmailMessage()
            msg["Subject"] = self.subject
            out = msg.as_bytes()
        parsed = Parser().parsestr(out.decode("utf-8"), headersonly=True)
        decoded, charset = decode_header(parsed["subject"])[0]
        self.assertEqual(self.subject, decoded.decode(charset))
