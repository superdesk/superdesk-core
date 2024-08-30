# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2016 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
#

"""Schema utils."""

import superdesk

from superdesk.lock import lock, unlock
from superdesk.core import get_app_config, get_current_app
from superdesk.commands.rebuild_elastic_index import RebuildElasticIndex

from .async_cli import cli


VERSION_ID = "schema_version"


def _get_version_db():
    """Get db used for storing version information."""
    return get_current_app().data.mongo.pymongo().db["superdesk"]


def get_schema_version():
    """Read app schema version from db."""
    db = _get_version_db()
    version = db.find_one({"_id": VERSION_ID})
    return version.get("version") if version else 0


def set_schema_version(version):
    """Store app schema version to db.

    :param version
    """
    db = _get_version_db()
    db.update_one({"_id": VERSION_ID}, {"$set": {"version": version}}, upsert=True)


def update_schema():
    """Run rebuild elastic index command to update schema."""
    RebuildElasticIndex().run()


@cli.register_async_command("schema:migrate")
async def schema_migrate_command():
    """Migrate elastic schema if needed, should be triggered on every deploy.

    It compares version set in code (latest) to one stored in db and only updates
    schema if those are different.

    Current version is read from settings and fallbacks to superdesk.SCHEMA_VERSION,
    so that you can avoid migration via settings file if needed.

    Example:
    ::

        $ python manage.py schema:migrate

    """

    return await schema_migrate_command_handler()


async def schema_migrate_command_handler():
    lock_name = "schema:migrate"

    if not lock(lock_name, expire=1800):
        return

    try:
        app_schema_version = get_schema_version()
        superdesk_schema_version = get_app_config("SCHEMA_VERSION", superdesk.SCHEMA_VERSION)
        if app_schema_version < superdesk_schema_version:
            print("Updating schema from version {} to {}.".format(app_schema_version, superdesk_schema_version))
            update_schema()
            set_schema_version(superdesk_schema_version)
        else:
            print("App already at version ({}).".format(app_schema_version))
    finally:
        unlock(lock_name)
