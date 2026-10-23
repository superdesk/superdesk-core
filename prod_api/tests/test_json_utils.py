import json
from copy import deepcopy
from datetime import datetime, timedelta, timezone

import pytest
from bson import ObjectId

from prod_api.json_utils import ProdApiJSONEncoder, ProdApiLegacyJSONEncoder
from superdesk.core.resources import Dataclass
from superdesk.core.resources.fields import UTCDatetime
from superdesk.core.types import BaseModel
from superdesk.flask import url_for


class ExampleModel(BaseModel):
    when: UTCDatetime


class ExampleDataclass(Dataclass):
    when: UTCDatetime


@pytest.mark.parametrize(
    "encoder_class, offset, non_utc_offset, z_offset",
    [
        (ProdApiJSONEncoder, "+00:00", "+02:00", "Z"),
        (ProdApiLegacyJSONEncoder, "+0000", "+0200", "+0000"),
    ],
)
def test_json_encoder_datetime_format(encoder_class, offset, non_utc_offset, z_offset):
    timestamp = datetime(2026, 10, 20, 7, 56, 49, tzinfo=timezone.utc)
    object_id = ObjectId()
    response = {
        "_id": object_id,
        "dates": [
            timestamp,
            timestamp.replace(tzinfo=None),
            "2026-10-20T07:56:49+0000",
            "2026-10-20T07:56:49+00:00",
        ],
        "model": ExampleModel(when=timestamp),
        "dataclass": ExampleDataclass(when=timestamp),
        "fractional": timestamp.replace(microsecond=123456, tzinfo=timezone(timedelta(hours=2))),
        "zulu": "2026-10-20T07:56:49Z",
        "unchanged": ["2026-10-20", "12:00", "urn:newsml:2026-10-20T07:56:49+0000", None, 42, False],
    }
    original = deepcopy(response)

    result = json.loads(encoder_class().encode(response))

    expected = "2026-10-20T07:56:49" + offset
    assert result == {
        "_id": str(object_id),
        "dates": [expected] * 4,
        "model": {"when": expected},
        "dataclass": {"when": expected},
        "fractional": "2026-10-20T07:56:49.123456" + non_utc_offset,
        "zulu": "2026-10-20T07:56:49" + z_offset,
        "unchanged": response["unchanged"],
    }
    assert response == original


@pytest.mark.parametrize(
    "prodapi_app_with_data, expected",
    [
        ({}, ("2019-07-04T22:00:00+00:00", "2019-07-04T22:00:00.000Z")),
        ({"PRODAPI_RFC3339_DATETIME": False}, ("2019-07-04T22:00:00+0000", "2019-07-04T22:00:00.000+0000")),
    ],
    indirect=["prodapi_app_with_data"],
)
async def test_events_response_datetime_format(prodapi_app_with_data, prodapi_app_with_data_client, expected):
    guid = "urn:newsml:localhost:5000:2019-08-22T15:50:04.266685:64201fdf-7462-4079-b914-60700b2bbf0c"

    async with prodapi_app_with_data.test_request_context("/"):
        response = await prodapi_app_with_data_client.get(
            url_for("events|resource", source=json.dumps({"query": {"ids": {"values": [guid]}}}))
        )
        assert response.status_code == 200
        items = (await response.get_json())["_items"]
        assert len(items) == 1

        response = await prodapi_app_with_data_client.get(url_for("events|item_lookup", _id=guid))
        assert response.status_code == 200

        for item in (items[0], await response.get_json()):
            assert item["dates"]["start"] in expected
            assert item["_planning_schedule"][0]["scheduled"] in expected
