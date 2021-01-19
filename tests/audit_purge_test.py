from bson import ObjectId
from datetime import datetime, timedelta
from superdesk.tests import TestCase
from superdesk.audit import PurgeAudit
from superdesk import get_resource_service


class AuditTestCase(TestCase):
    def testAuditPurge(self):
        now = datetime.utcnow()
        self.app.data.insert("archive", [{"_id": 2}])
        self.app.data.insert(
            "audit",
            [
                {"_id": ObjectId.from_datetime(now - timedelta(minutes=50)), "resource": "user"},
                {
                    "_id": ObjectId.from_datetime(now - timedelta(minutes=30)),
                    "resource": "archive",
                    "extra": {"guid": 2},
                    "audit_id": 2,
                },
                {
                    "_id": ObjectId.from_datetime(now - timedelta(minutes=10)),
                    "resource": "archive",
                    "extra": {"guid": 3},
                    "audit_id": 3,
                },
                {"_id": ObjectId(), "resource": "archive_autosave", "audit_id": 4},
            ],
        )
        self.app.config["AUDIT_EXPIRY_MINUTES"] = 5
        PurgeAudit().run()
        self.assertEqual(get_resource_service("audit").find({}).count(), 1)
