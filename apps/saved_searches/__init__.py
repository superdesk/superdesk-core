# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license
import logging
from typing import Any

from flask_babel import lazy_gettext
import superdesk
from superdesk.celery_app import celery
from superdesk.lock import lock, unlock
from .saved_searches import (
    SavedSearchesService,
    SavedSearchesResource,
    AllSavedSearchesResource,
    SavedSearchItemsResource,
    SavedSearchItemsService,
    AllSavedSearchesService,
)
from superdesk import get_resource_service
from superdesk import es_utils
from superdesk.privilege import GLOBAL_SEARCH_PRIVILEGE
import pytz
from croniter import croniter
from datetime import datetime
from flask import render_template
from superdesk import emails
import json

logger = logging.getLogger(__name__)
REPORT_SOFT_LIMIT = 60 * 5
LOCK_NAME = "saved_searches_report"


def init_app(app) -> None:
    endpoint_name = "saved_searches"
    service: Any = SavedSearchesService(endpoint_name, backend=superdesk.get_backend())
    SavedSearchesResource(endpoint_name, app=app, service=service)

    endpoint_name = "all_saved_searches"
    service = AllSavedSearchesService(endpoint_name, backend=superdesk.get_backend())
    AllSavedSearchesResource(endpoint_name, app=app, service=service)

    endpoint_name = "saved_search_items"
    service = SavedSearchItemsService(endpoint_name, backend=superdesk.get_backend())
    SavedSearchItemsResource(endpoint_name, app=app, service=service)

    superdesk.privilege(
        name=GLOBAL_SEARCH_PRIVILEGE,
        label=lazy_gettext("Global searches"),
        description=lazy_gettext("Use global saved searches."),
    )
    superdesk.privilege(
        name="global_saved_searches",
        label=lazy_gettext("Manage Global Saved Searches"),
        description=lazy_gettext("User can manage other users' global saved searches"),
    )
    superdesk.privilege(
        name="saved_searches",
        label=lazy_gettext("Manage Saved Searches"),
        description=lazy_gettext("User can manage saved searches"),
    )
    superdesk.privilege(
        name="saved_searches_subscriptions",
        label=lazy_gettext("Manage Saved Searches Subscriptions"),
        description=lazy_gettext("User can (un)subscribe to saved searches"),
    )
    superdesk.privilege(
        name="saved_searches_subscriptions_admin",
        label=lazy_gettext("Manage Saved Searches Subscriptions For Other Users"),
        description=lazy_gettext("User manage other users saved searches subscriptions"),
    )


def get_next_date(scheduling, base=None):
    """Get next schedule date

    :param str scheduling: task schedule, using cron syntax
    :return datetime: date of next schedule
    """
    if base is None:
        tz = pytz.timezone(superdesk.app.config["DEFAULT_TIMEZONE"])
        base = datetime.now(tz=tz)
    cron_iter = croniter(scheduling, base)
    return cron_iter.get_next(datetime)


def send_report_email(user_id, search, docs):
    """Send saved search report by email.

    :param dict search: saved search data
    :param list found_items: items matching the search request
    """
    users_service = get_resource_service("users")
    user_data = next(users_service.find({"_id": user_id}))
    recipients = [user_data["email"]]
    app = superdesk.app
    admins = app.config["ADMINS"]
    subject = "Saved searches report"
    context = {
        "app_name": app.config["APPLICATION_NAME"],
        "search": search,
        "docs": docs,
        "client_url": app.config["CLIENT_URL"].rstrip("/"),
    }
    text_body = render_template("saved_searches_report.txt", **context)
    html_body = render_template("saved_searches_report.html", **context)
    emails.send_email.delay(
        subject=subject, sender=admins[0], recipients=recipients, text_body=text_body, html_body=html_body
    )


def publish_report(user_id, search_data):
    """Create report for a search and send it by email"""
    search_filter = json.loads(search_data["filter"])
    query = es_utils.filter2query(search_filter, user_id=user_id)
    repos = es_utils.filter2repos(search_filter) or es_utils.REPOS.copy()
    docs = list(superdesk.app.data.elastic.search(query, repos))
    send_report_email(user_id, search_data, docs)


def process_subscribers(subscribers, search, now, isDesk=False):
    do_update = False

    for subscriber_data in subscribers:
        scheduling = subscriber_data["scheduling"]
        next_report = subscriber_data.get("next_report")
        if next_report is None:
            subscriber_data["next_report"] = get_next_date(scheduling)
            do_update = True
        elif next_report <= now:
            if isDesk:
                desk = get_resource_service("desks").find_one(req=None, _id=subscriber_data["desk"])
                for member in (desk or {}).get("members", []):
                    publish_report(member.get("user"), search)
            else:
                publish_report(subscriber_data["user"], search)
            subscriber_data["last_report"] = now
            subscriber_data["next_report"] = get_next_date(scheduling)
            do_update = True

    return do_update


@celery.task(soft_time_limit=REPORT_SOFT_LIMIT)
def report():
    """Check all saved_searches with subscribers, and publish reports"""
    if not lock(LOCK_NAME, expire=REPORT_SOFT_LIMIT + 10):
        return
    try:
        saved_searches = get_resource_service("saved_searches")
        subscribed_searches = saved_searches.find({"subscribers": {"$exists": 1}})
        tz = pytz.timezone(superdesk.app.config["DEFAULT_TIMEZONE"])
        now = datetime.now(tz=tz)
        for search in subscribed_searches:
            do_update = False

            subscribed_users = search["subscribers"].get("user_subscriptions", [])
            try:
                do_update = process_subscribers(subscribed_users, search, now, False) or do_update
            except Exception as e:
                logger.error(
                    "Can't do saved search report for users:\nexception: {e}\ndata: {search}".format(e=e, search=search)
                )

            subscribed_desks = search["subscribers"].get("desk_subscriptions", [])
            try:
                do_update = process_subscribers(subscribed_desks, search, now, True) or do_update
            except Exception as e:
                logger.error(
                    "Can't do saved search report for desks:\nexception: {e}\ndata: {search}".format(e=e, search=search)
                )

            if do_update:
                updates = {"subscribers": search["subscribers"]}
                saved_searches.system_update(search["_id"], updates, search)
    except Exception as e:
        logger.error("Can't report saved searches: {reason}".format(reason=e))
    finally:
        unlock(LOCK_NAME)
