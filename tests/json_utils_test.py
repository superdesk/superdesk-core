import datetime

from superdesk.json_utils import try_cast, SuperdeskJSONEncoder


def test_json_encoder():
    encoder = SuperdeskJSONEncoder()

    # Test datetime serialization
    dt = datetime.datetime(2023, 1, 1, 12, 0, 0)
    assert encoder.default(dt) == "2023-01-01T12:00:00+0000"


def test_try_cast():
    assert try_cast("2023-01-01T12:00:00+0000") == datetime.datetime(2023, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)
    assert try_cast("not_a_number") == "not_a_number"
