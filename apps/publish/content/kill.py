# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import json
import html
from flask import render_template

from eve.versioning import resolve_document_version
from apps.templates.content_templates import render_content_template_by_name
from .common import BasePublishService, BasePublishResource, ITEM_KILL
from eve.utils import config
from superdesk.metadata.item import CONTENT_STATE, ITEM_STATE, PUB_STATUS, EMBARGO, SCHEDULE_SETTINGS, \
    PUBLISH_SCHEDULE
from superdesk import get_resource_service
from superdesk.utc import utcnow
import logging
from copy import deepcopy
from superdesk.emails import send_article_killed_email
from superdesk.errors import SuperdeskApiError
from apps.archive.common import ITEM_OPERATION, ARCHIVE, insert_into_versions, get_dateline_city
from itertools import chain
from apps.publish.published_item import PUBLISHED, LAST_PUBLISHED_VERSION
from flask_babel import _

logger = logging.getLogger(__name__)


class KillPublishResource(BasePublishResource):
    def __init__(self, endpoint_name, app, service):
        super().__init__(endpoint_name, app, service, 'kill')


class KillPublishService(BasePublishService):
    publish_type = 'kill'
    published_state = 'killed'
    item_operation = ITEM_KILL

    def __init__(self, datasource=None, backend=None):
        super().__init__(datasource=datasource, backend=backend)

    def on_update(self, updates, original):
        # check if we are trying to kill and item that is contained in package
        # and the package itself is not killed.

        packages = self.package_service.get_packages(original[config.ID_FIELD])
        if packages and packages.count() > 0:
            for package in packages:
                if package[ITEM_STATE] not in {CONTENT_STATE.KILLED, CONTENT_STATE.RECALLED}:
                    raise SuperdeskApiError.badRequestError(message=_(
                        'This item is in a package. It needs to be removed before the item can be killed'))

        updates['pubstatus'] = PUB_STATUS.CANCELED
        updates['versioncreated'] = utcnow()

        super().on_update(updates, original)
        updates[ITEM_OPERATION] = self.item_operation
        get_resource_service('archive_broadcast').spike_item(original)

    def update(self, id, updates, original):
        """Kill will broadcast kill email notice to all subscriber in the system and then kill the item.

        Kill for multiple items is triggered
        - for broadcast items if master item is killed.
        In case of the multiple items the kill header text will be different but rest
        of the body_html will be same.

        If any other fields needs in the kill template that needs to be based on the item that is being
        killed (not the item that is being actioned on) then modify the article_killed_override.json file'
        """
        # kill cannot be scheduled and embargoed.
        updates[EMBARGO] = None
        updates[PUBLISH_SCHEDULE] = None
        updates[SCHEDULE_SETTINGS] = {}
        updates_copy = deepcopy(updates)
        original_copy = deepcopy(original)
        self.apply_kill_override(original_copy, updates)
        self.broadcast_kill_email(original, updates)
        super().update(id, updates, original)
        updated = deepcopy(original)
        updated.update(updates)
        get_resource_service('archive_broadcast').kill_broadcast(updates_copy, original_copy, self.item_operation)

    def broadcast_kill_email(self, original, updates):
        """Sends the broadcast email to all subscribers (including in-active subscribers)

        :param dict original: Document to kill
        :param dict updates: kill updates
        """
        # Get all subscribers
        subscribers = list(get_resource_service('subscribers').get(req=None, lookup=None))

        recipients = [s.get('email').split(',') for s in subscribers if s.get('email')]
        recipients = list(set(chain(*recipients)))
        # send kill email.
        kill_article = deepcopy(original)
        kill_article['body_html'] = updates.get('body_html')
        kill_article['headline'] = updates.get('headline')
        kill_article['desk_name'] = get_resource_service('desks').get_desk_name(kill_article.get('task',
                                                                                                 {}).get('desk'))
        kill_article['city'] = get_dateline_city(kill_article.get('dateline'))
        kill_article['action'] = self.item_operation
        send_article_killed_email(kill_article, recipients, utcnow())

    def kill_item(self, updates, original):
        """Kill the item after applying the template.

        :param dict updates:
        :param dict original:
        """
        # apply the kill template
        original_copy = deepcopy(original)
        updates_data = self.apply_kill_template(original_copy)
        updates_data['body_html'] = updates.get('body_html', '')
        # resolve the document version
        resolve_document_version(document=updates_data, resource=ARCHIVE, method='PATCH', latest_doc=original)
        # kill the item
        self.patch(original.get(config.ID_FIELD), updates_data)
        # insert into versions
        insert_into_versions(id_=original[config.ID_FIELD])

    def apply_kill_template(self, item):
        # apply the kill template
        updates = render_content_template_by_name(item, self.item_operation)
        return updates

    def apply_kill_override(self, item, updates):
        """Applies kill override.

        Kill requires content to be generate based on the item getting killed (and not the
        item that is being actioned on).

        :param dict item: item to kill
        :param dict updates: updates that needs to be modified based on the template
        :return:
        """
        try:
            if item.get('_type') == 'archive':
                # attempt to find the published item as this will have an accurate time of publication
                published_items = get_resource_service(PUBLISHED).get_last_published_version(item.get(config.ID_FIELD))
                published_item = [p for p in published_items if p.get(LAST_PUBLISHED_VERSION)][0] \
                    if published_items.count() > 0 else None
                versioncreated = published_item.get('versioncreated') if published_item else \
                    item.get('versioncreated', item.get(config.LAST_UPDATED))
            else:
                versioncreated = item.get('versioncreated', item.get(config.LAST_UPDATED))
            desk_name = get_resource_service('desks').get_desk_name(item.get('task', {}).get('desk'))
            city = get_dateline_city(item.get('dateline'))
            kill_header = json.loads(render_template('article_killed_override.json',
                                                     slugline=item.get('slugline', ''),
                                                     headline=item.get('headline', ''),
                                                     desk_name=desk_name,
                                                     city=city,
                                                     versioncreated=versioncreated,
                                                     body_html=updates.get('body_html', ''),
                                                     update_headline=updates.get('headline', ''),
                                                     item_operation=self.item_operation.lower()),
                                     strict=False)

            for key, value in kill_header.items():
                kill_header[key] = html.unescape(value)

            updates.update(kill_header)
        except Exception:
            logger.exception('Failed to apply kill header template to item {}.'.format(item))
