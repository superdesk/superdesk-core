from datetime import datetime, timezone

from superdesk.core.resources import BaseModel, Dataclass
from superdesk.json_utils import SuperdeskJSONEncoder


class ProdApiJSONEncoder(SuperdeskJSONEncoder):
    """Serialize Production API datetimes as RFC 3339 without changing stored data."""

    rfc3339 = True

    def default(self, obj):
        if isinstance(obj, datetime):
            # MongoDB can return naive datetimes, which represent UTC.
            if obj.tzinfo is None:
                obj = obj.replace(tzinfo=timezone.utc)
            if self.rfc3339:
                return obj.isoformat()
            return (
                obj.strftime("%Y-%m-%dT%H:%M:%S")
                + (f".{obj.microsecond:06d}" if obj.microsecond else "")
                + obj.strftime("%z")
            )
        if isinstance(obj, (BaseModel, Dataclass)):
            # Python mode preserves datetime types, including nested model fields.
            return obj.to_dict()
        return super().default(obj)


class ProdApiLegacyJSONEncoder(ProdApiJSONEncoder):
    """Use compact timezone offsets for clients requiring the legacy datetime format."""

    rfc3339 = False
