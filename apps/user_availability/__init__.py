from celery.schedules import crontab
from superdesk.celery_app import celery

endpoint_name = "user_availability"
default_endpoint_name = "default_user_availability"

from .availability import AvailabilityResource, availability_service
from .default_availability import DefaultAvailabilityResource, default_service


def init_app(app):
    AvailabilityResource(endpoint_name, app=app, service=availability_service)
    DefaultAvailabilityResource(default_endpoint_name, app=app, service=default_service)

    # generate availability for all users once a day
    app.config["CELERY_BEAT_SCHEDULE"]["user_availability:generate-scheduled-rundowns"] = {
        "task": "apps.user_availability.generate_user_availability",
        "schedule": crontab(hour="1", minute="40"),
    }


@celery.task
def generate_user_availability():
    """
    Generate user availability for all users.
    """
    default_service.generate_all_users_availability()
