import pytz
from behave import when, then  # type: ignore
from datetime import datetime, timedelta
from superdesk.tests import set_placeholder
from superdesk.tests.steps import get_json_data, parse_date
from superdesk.utc import utcnow, local_to_utc


@when("we run create content task")
def when_we_run_create_content_task(context):
    from apps.templates import create_scheduled_content

    now = utcnow() + timedelta(days=8)
    with context.app.app_context():
        items = create_scheduled_content(now)
        for item in items:
            set_placeholder(context, "ITEM_ID", str(item["_id"]))


@then('next run is on monday "{time}"')
def then_next_run_is_on_monday(context, time):
    data = get_json_data(context.response)
    next_run = parse_date(data.get("next_run"))
    fmt = "%H:%M:%S"

    try:
        # assume time is set in given time zone
        tz = pytz.timezone(data["schedule"]["time_zone"])
    except KeyError:
        # fallback to utc
        tz = pytz.utc

    parsed = datetime.strptime(time, fmt)
    expected = datetime.now(tz)
    expected = expected.replace(hour=parsed.hour, minute=parsed.minute, second=parsed.second, microsecond=0)

    if expected < utcnow():  # make sure it's monday in future
        expected = expected + timedelta(days=(7 - expected.weekday()))

    expected_utc = local_to_utc(tz.zone, expected)

    assert isinstance(next_run, datetime)
    if tz.zone == "Australia/Sydney":
        assert next_run.weekday() == 6
    else:
        assert next_run.weekday() == 0
    assert next_run.strftime(fmt) == expected_utc.strftime(fmt), "next run %s is not expected %s" % (
        next_run.strftime(fmt),
        expected_utc.strftime(fmt),
    )
