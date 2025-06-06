import superdesk

from flask_babel import lazy_gettext
from celery.schedules import crontab
from superdesk.celery_app import celery

from .privileges import USER_AVAILABILITY_READ, USER_AVAILABILITY_WRITE
from .availability import AvailabilityResource, availability_service
from .default_availability import DefaultAvailabilityResource, default_service


def init_app(app):
    AvailabilityResource(availability_service.datasource, app=app, service=availability_service)
    DefaultAvailabilityResource(default_service.datasource, app=app, service=default_service)

    availability_service.default_service = default_service
    default_service.availability_service = availability_service

    # generate availability for all users once a day
    app.config["CELERY_BEAT_SCHEDULE"]["user_availability:generate-scheduled-rundowns"] = {
        "task": "apps.user_availability.generate_user_availability",
        "schedule": crontab(hour="1", minute="40"),
    }

    superdesk.privilege(
        name=USER_AVAILABILITY_READ,
        label=lazy_gettext("Availability - view"),
        description=lazy_gettext("User can view availability dashboard"),
    )

    superdesk.privilege(
        name=USER_AVAILABILITY_WRITE,
        label=lazy_gettext("Availability - manage"),
        description=lazy_gettext("User can overwrite availability settings that each user has set"),
    )


@celery.task
def generate_user_availability():
    """
    Generate user availability for all users.
    """
    default_service.generate_all_users_availability()
