"""Celery entrypoint.

Usage via Procfile:

    work: celery -A superdesk.worker worker
    beat: celery -A superdesk.worker beat --pid=

"""

from superdesk.factory import get_app

celery = get_app().celery
