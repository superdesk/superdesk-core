import superdesk
from apps.analytics.activityreports import ActivityReportResource, ActivityReportService


def init_app(app):
    endpoint_name = 'activityreports'
    service = ActivityReportService(endpoint_name, backend=superdesk.get_backend())
    ActivityReportResource(endpoint_name, app=app, service=service)

    superdesk.privilege(name='activityreports', label='Activity Report View',
                        description='User can view activity reports.')
