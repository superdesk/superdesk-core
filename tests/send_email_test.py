from superdesk.emails import send_user_status_changed_email, send_activity_emails, send_email, send_translation_changed
from superdesk.tests import TestCase
from unittest.mock import patch


class SendEmailTestCase(TestCase):
    def test_send_email(self):
        with self.app.app_context():
            with self.app.mail.record_messages() as outbox:
                assert len(outbox) == 0
                send_user_status_changed_email(["test@sd.io"], "created")
                assert len(outbox) == 1
                assert outbox[0].subject == "Your Superdesk account is created"

    def test_send_email_multiline_subject(self):
        with self.app.app_context():
            with self.app.mail.record_messages() as outbox:
                send_email("foo\nbar", "admin@localhost", ["foo@example.com"], "text", "<p>html</p>")
                assert len(outbox) == 1
                assert outbox[0].subject == "foo"

    def test_send_activity_emails_error(self):
        recipients = ["foo", "bar"]
        activities = [
            {"message": "error", "data": {"foo": 1}},
            {"message": "error", "data": {"bar": 1}},
        ]
        with patch.object(send_email, "delay", return_value=None) as sent:
            with self.app.app_context():
                send_activity_emails(activities[0], recipients)
                self.assertEqual(1, sent.call_count)
                send_activity_emails(activities[0], recipients)
                self.assertEqual(1, sent.call_count)
                send_activity_emails(activities[1], recipients)
                self.assertEqual(2, sent.call_count)
                send_activity_emails(activities[1], recipients)
                self.assertEqual(2, sent.call_count)

    def test_send_translation_changed(self):
        item = {"_id": "test_id", "guid": "guid", "headline": "headline test"}
        with self.app.app_context():
            with self.app.mail.record_messages() as outbox:
                assert len(outbox) == 0
                send_translation_changed("admin", item, ["test@sd.io"])
                assert len(outbox) == 1
                assert outbox[0].subject == "The original item headline test has been changed"
                link = "http://localhost:9000/#/workspace?item=guid&action=edit"
                assert outbox[0].body.find(link) != -1
                assert outbox[0].html.find(link) != -1
