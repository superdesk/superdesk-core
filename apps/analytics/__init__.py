import superdesk
from apps.analytics.activity_reports import ActivityReportResource, ActivityReportService


def init_app(app):
    endpoint_name = 'activity_reports'
    service = ActivityReportService(endpoint_name, backend=superdesk.get_backend())
    ActivityReportResource(endpoint_name, app=app, service=service)

    superdesk.privilege(name='activity_reports', label='Activity Report View',
                        description='User can view activity reports.')
