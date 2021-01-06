from superdesk.tests import TestCase
from superdesk.audit import PurgeAudit
from superdesk import get_resource_service


class AuditTestCase(TestCase):
    def testAuditPurge(self):
        self.app.data.insert("archive", [{"_id": 2}])
        # audit 1 and 3 will get deleted, 2 will survive as it has a related item in archive
        self.app.data.insert(
            "audit",
            [
                {"_id": 1, "resource": "user"},
                {"_id": 2, "resource": "archive", "extra": {"guid": 2}, "audit_id": 2},
                {"_id": 3, "resource": "archive", "extra": {"guid": 3}, "audit_id": 3},
                {"_id": 4, "resource": "archive_autosave", "audit_id": 4},
            ],
        )
        self.app.config["AUDIT_EXPIRY_MINUTES"] = -10

        PurgeAudit().run()
        self.assertEqual(get_resource_service("audit").find({}).count(), 1)
