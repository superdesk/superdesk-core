from superdesk.emails import send_user_status_changed_email
from superdesk.tests import TestCase


class SendEmailTestCase(TestCase):

    def test_send_email(self):
        with self.app.app_context():
            with self.app.mail.record_messages() as outbox:
                assert len(outbox) == 0
                send_user_status_changed_email(['test@sd.io'], 'created')
                assert len(outbox) == 1
                assert outbox[0].subject == 'Your Superdesk account is created'
