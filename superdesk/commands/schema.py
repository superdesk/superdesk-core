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

from flask import current_app as app
from superdesk.lock import lock, unlock
from superdesk.commands.rebuild_elastic_index import RebuildElasticIndex


VERSION_ID = 'schema_version'


def _get_version_db():
    """Get db used for storing version information."""
    return app.data.mongo.pymongo().db['superdesk']


def get_schema_version():
    """Read app schema version from db."""
    db = _get_version_db()
    version = db.find_one({'_id': VERSION_ID})
    return version.get('version') if version else 0


def set_schema_version(version):
    """Store app schema version to db.

    :param version
    """
    db = _get_version_db()
    db.update_one({'_id': VERSION_ID}, {'$set': {'version': version}}, upsert=True)


def update_schema():
    """Run rebuild elastic index command to update schema."""
    RebuildElasticIndex().run()


class SchemaMigrateCommand(superdesk.Command):
    """Migrate elastic schema if needed, should be triggered on every deploy.

    It compares version set in code (latest) to one stored in db and only updates
    schema if those are different.

    Current version is read from settings and fallbacks to superdesk.SCHEMA_VERSION,
    so that you can avoid migration via settings file if needed.

    Example:
    ::

        $ python manage.py schema:migrate

    """

    def run(self):
        lock_name = 'schema:migrate'

        if not lock(lock_name, expire=1800):
            return

        try:
            app_schema_version = get_schema_version()
            superdesk_schema_version = app.config.get('SCHEMA_VERSION', superdesk.SCHEMA_VERSION)
            if app_schema_version < superdesk.SCHEMA_VERSION:
                print('Updating schema from version {} to {}.'.format(
                    app_schema_version, superdesk_schema_version
                ))
                update_schema()
                set_schema_version(superdesk_schema_version)
            else:
                print('App already at version ({}).'.format(app_schema_version))
        finally:
            unlock(lock_name)


superdesk.command('schema:migrate', SchemaMigrateCommand())
