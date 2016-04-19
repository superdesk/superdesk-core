
from datetime import datetime, timedelta
from superdesk.tests import set_placeholder
from steps import when, then, get_json_data, parse_date  # @UnresolvedImport
from superdesk.utc import utcnow


@when('we run create content task')
def when_we_run_create_content_task(context):
    from apps.templates import create_scheduled_content
    now = utcnow() + timedelta(days=8)
    with context.app.app_context():
        items = create_scheduled_content(now)
        for item in items:
            set_placeholder(context, 'ITEM_ID', str(item['_id']))


@then('next run is on monday "{time}"')
def then_next_run_is_on_monday(context, time):
    data = get_json_data(context.response)
    next_run = parse_date(data.get('next_run'))
    assert isinstance(next_run, datetime)
    assert next_run.weekday() == 0
    assert next_run.strftime('%H:%M:%S') == time, 'it is %s' % (next_run, )
