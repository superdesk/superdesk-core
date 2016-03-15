from superdesk.emails import send_user_status_changed_email, send_activity_emails, send_email
from superdesk.tests import TestCase
from unittest.mock import patch


class SendEmailTestCase(TestCase):

    def test_send_email(self):
        with self.app.app_context():
            with self.app.mail.record_messages() as outbox:
                assert len(outbox) == 0
                send_user_status_changed_email(['test@sd.io'], 'created')
                assert len(outbox) == 1
                assert outbox[0].subject == 'Your Superdesk account is created'

    def test_send_activity_emails_error(self):
        recipients = ['foo', 'bar']
        activities = [
            {'message': 'error', 'data': {'foo': 1}},
            {'message': 'error', 'data': {'bar': 1}},
        ]
        with patch.object(send_email, 'delay', return_value=None) as sent:
            with self.app.app_context():
                send_activity_emails(activities[0], recipients)
                self.assertEqual(1, sent.call_count)
                send_activity_emails(activities[0], recipients)
                self.assertEqual(1, sent.call_count)
                send_activity_emails(activities[1], recipients)
                self.assertEqual(2, sent.call_count)
                send_activity_emails(activities[1], recipients)
                self.assertEqual(2, sent.call_count)
