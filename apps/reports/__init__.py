import superdesk
from apps.reports.resource import ActivityReportResource
from apps.reports.service import ActivityReportService


def init_app(app):
    endpoint_name = 'activityreports'
    service = ActivityReportService(endpoint_name, backend=superdesk.get_backend())
    ActivityReportResource(endpoint_name, app=app, service=service)

    superdesk.privilege(name='activityreports', label='Activity Report Management',
                        description='User can manage activity reports.')