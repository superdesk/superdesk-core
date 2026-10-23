import re
from datetime import datetime, timezone

from superdesk.json_utils import SuperdeskJSONEncoder


_DATETIME = re.compile(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?)(Z|[+-]\d{2}:?\d{2})")


def _normalize_datetime_strings(value: object, rfc3339: bool) -> object:
    if isinstance(value, str):
        match = _DATETIME.fullmatch(value)
        if match:
            offset = match[2]
            if rfc3339:
                if offset != "Z" and ":" not in offset:
                    offset = f"{offset[:3]}:{offset[3:]}"
            else:
                offset = "+0000" if offset == "Z" else offset.replace(":", "")
            return f"{match[1]}{offset}"
    elif isinstance(value, dict):
        return {key: _normalize_datetime_strings(item, rfc3339) for key, item in value.items()}
    elif isinstance(value, (list, tuple)):
        return [_normalize_datetime_strings(item, rfc3339) for item in value]
    return value


class ProdApiJSONEncoder(SuperdeskJSONEncoder):
    """Serialize Production API datetimes as RFC 3339 without changing stored data."""

    rfc3339 = True

    def default(self, obj):
        if isinstance(obj, datetime):
            # MongoDB can return naive datetimes, which represent UTC.
            if obj.tzinfo is None:
                obj = obj.replace(tzinfo=timezone.utc)
            return _normalize_datetime_strings(obj.isoformat(), self.rfc3339)
        return _normalize_datetime_strings(super().default(obj), self.rfc3339)

    def iterencode(self, obj):
        # Elasticsearch and Pydantic may have already serialized datetime values.
        return super().iterencode(_normalize_datetime_strings(obj, self.rfc3339))


class ProdApiLegacyJSONEncoder(ProdApiJSONEncoder):
    """Use compact timezone offsets for clients requiring the legacy datetime format."""

    rfc3339 = False
