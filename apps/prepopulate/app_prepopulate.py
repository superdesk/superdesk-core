# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import os
import json
import flask
import logging
import superdesk
import multiprocessing
import werkzeug.exceptions

from flask import current_app as app
from eve.utils import date_to_str
from eve.versioning import insert_versioning_documents
from bson.objectid import ObjectId
from apps.archive.common import ITEM_OPERATION
from superdesk import get_resource_service
from superdesk.metadata.item import ITEM_STATE, CONTENT_STATE
from superdesk.resource import Resource
from superdesk.services import BaseService
from superdesk.tests import clean_dbs, use_snapshot
from superdesk.utc import utcnow
from superdesk.timer import timer
from apps.search_providers import allowed_search_providers, register_search_provider


logger = logging.getLogger(__name__)


def apply_placeholders(placeholders, text):
    if not placeholders or not text:
        return text
    for tag, value in placeholders.items():
        text = text.replace(tag, value)
    return text


def set_logged_user(username, password):
    auth_token = get_resource_service("auth").find_one(username=username, req=None)
    if not auth_token:
        user = {"username": username, "password": password}
        get_resource_service("auth_db").post([user])
        auth_token = get_resource_service("auth").find_one(username=username, req=None)
    flask.g.user = get_resource_service("users").find_one(req=None, username=username)
    flask.g.auth = auth_token


def get_default_user():
    user = {
        "username": "test_user",
        "password": "test_password",
        "user_type": "administrator",
        "is_active": True,
        "needs_activation": False,
        "first_name": "first name",
        "last_name": "last name",
        "email": "test_user@test.com",
    }
    return user


def prepopulate_data(file_name, default_user=None, directory=None):
    if default_user is None:
        default_user = get_default_user()

    if not directory:
        directory = os.path.abspath(os.path.dirname(__file__))
    placeholders = {"NOW()": date_to_str(utcnow())}
    users = {default_user["username"]: default_user["password"]}
    default_username = default_user["username"]
    file = os.path.join(directory, file_name)
    with open(file, "rt", encoding="utf8") as app_prepopulation:
        json_data = json.load(app_prepopulation)
        for item in json_data:
            resource = item.get("resource", None)
            try:
                service = get_resource_service(resource)
            except KeyError:
                continue  # resource which is not configured - ignore
            username = item.get("username", None) or default_username
            set_logged_user(username, users[username])
            id_name = item.get("id_name", None)
            id_update = item.get("id_update", None)
            text = json.dumps(item.get("data", None))
            text = apply_placeholders(placeholders, text)
            data = json.loads(text)
            if resource:
                app.data.mongo._mongotize(data, resource)
            if resource == "users":
                users.update({data["username"]: data["password"]})
            if id_update:
                id_update = apply_placeholders(placeholders, id_update)
                res = service.patch(ObjectId(id_update), data)
                if not res:
                    raise Exception()
            else:
                try:
                    ids = service.post([data])
                except werkzeug.exceptions.Conflict:
                    # instance was already prepopulated
                    break
                except superdesk.errors.SuperdeskApiError as e:
                    logger.exception(e)
                    continue  # an error raised by validation
                if not ids:
                    raise Exception()
                if id_name:
                    placeholders[id_name] = str(ids[0])

            if app.config["VERSION"] in data:
                number_of_versions_to_insert = data[app.config["VERSION"]]
                doc_versions = []

                if data[ITEM_STATE] not in [CONTENT_STATE.PUBLISHED, CONTENT_STATE.CORRECTED, CONTENT_STATE.KILLED]:
                    while number_of_versions_to_insert != 0:
                        doc_versions.append(data.copy())
                        number_of_versions_to_insert -= 1
                else:
                    if data[ITEM_STATE] in [CONTENT_STATE.KILLED, CONTENT_STATE.RECALLED, CONTENT_STATE.CORRECTED]:
                        latest_version = data.copy()
                        doc_versions.append(latest_version)

                        published_version = data.copy()
                        published_version[ITEM_STATE] = CONTENT_STATE.PUBLISHED
                        published_version[ITEM_OPERATION] = "publish"
                        published_version[app.config["VERSION"]] = number_of_versions_to_insert - 1
                        doc_versions.append(published_version)

                        number_of_versions_to_insert -= 2
                    elif data[ITEM_STATE] == CONTENT_STATE.PUBLISHED:
                        published_version = data.copy()
                        doc_versions.append(published_version)
                        number_of_versions_to_insert -= 1

                    while number_of_versions_to_insert != 0:
                        doc = data.copy()
                        doc[ITEM_STATE] = CONTENT_STATE.PROGRESS
                        doc.pop(ITEM_OPERATION, "")
                        doc[app.config["VERSION"]] = number_of_versions_to_insert
                        doc_versions.append(doc)

                        number_of_versions_to_insert -= 1

                insert_versioning_documents(resource, doc_versions if doc_versions else data)


prepopulate_schema = {
    "profile": {"type": "string", "required": False, "default": "app_prepopulate_data"},
    "remove_first": {"type": "boolean", "required": False, "default": True},
}


class PrepopulateResource(Resource):
    """Prepopulate application data."""

    schema = prepopulate_schema
    resource_methods = ["POST"]
    public_methods = ["POST"]


class PrepopulateService(BaseService):
    def _create(self, docs):
        for doc in docs:
            if doc.get("remove_first"):
                clean_dbs(app, force=True)

            app.init_indexes()
            app.data.init_elastic(app)

            get_resource_service("users").stop_updating_stage_visibility()

            user = get_resource_service("users").find_one(username=get_default_user()["username"], req=None)
            if not user:
                get_resource_service("users").post([get_default_user()])

            prepopulate_data(doc.get("profile") + ".json", get_default_user())

            get_resource_service("users").start_updating_stage_visibility()
            get_resource_service("users").update_stage_visibility_for_users()

    def create(self, docs, **kwargs):
        with multiprocessing.Lock() as lock:
            with timer("prepopulate"):
                self._create(docs)
            if app.config.get("SUPERDESK_TESTING"):
                for provider in ["paimg", "aapmm"]:
                    if provider not in allowed_search_providers:
                        register_search_provider(provider, provider)
            return ["OK"]


class AppPrepopulateCommand(superdesk.Command):
    """Prepopulate Superdesk using sample data.

    Useful for demo/development environment, but don't run in production,
    it's hard to get rid of such data later.

    Example:
    ::

        $ python manage.py app:prepopulate

    """

    option_list = [
        superdesk.Option("--file", "-f", dest="prepopulate_file", default="app_prepopulate_data.json"),
        superdesk.Option("--dir", "-d", dest="directory", default=None),
    ]

    def run(self, prepopulate_file, directory=None):
        user = get_resource_service("users").find_one(username=get_default_user()["username"], req=None)
        if not user:
            get_resource_service("users").post([get_default_user()])
        prepopulate_data(prepopulate_file, get_default_user(), directory)


superdesk.command("app:prepopulate", AppPrepopulateCommand())
