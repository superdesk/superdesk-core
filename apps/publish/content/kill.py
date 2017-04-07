# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from eve.versioning import resolve_document_version
from .common import BasePublishService, BasePublishResource, ITEM_KILL
from eve.utils import config
from superdesk.metadata.item import CONTENT_STATE, ITEM_STATE, GUID_FIELD, PUB_STATUS, EMBARGO, SCHEDULE_SETTINGS, \
    PUBLISH_SCHEDULE
from superdesk.metadata.packages import PACKAGE_TYPE
from superdesk import get_resource_service
from superdesk.utc import utcnow
import logging
from copy import deepcopy
from superdesk.emails import send_article_killed_email
from superdesk.errors import SuperdeskApiError
from apps.archive.common import ITEM_OPERATION, ARCHIVE, insert_into_versions, get_dateline_city
from itertools import chain

logger = logging.getLogger(__name__)


class KillPublishResource(BasePublishResource):
    def __init__(self, endpoint_name, app, service):
        super().__init__(endpoint_name, app, service, 'kill')


class KillPublishService(BasePublishService):
    publish_type = 'kill'
    published_state = 'killed'

    def __init__(self, datasource=None, backend=None):
        super().__init__(datasource=datasource, backend=backend)

    def on_update(self, updates, original):
        # check if we are trying to kill and item that is contained in normal non takes package
        # and the package itself is not killed.

        packages = self.package_service.get_packages(original[config.ID_FIELD])
        if packages and packages.count() > 0:
            for package in packages:
                if package[ITEM_STATE] != CONTENT_STATE.KILLED and package.get(PACKAGE_TYPE, '') == '':
                    raise SuperdeskApiError.badRequestError(message='This item is in a package. '
                                                                    'It needs to be removed '
                                                                    'before the item can be killed')

        updates['pubstatus'] = PUB_STATUS.CANCELED
        updates['versioncreated'] = utcnow()

        super().on_update(updates, original)
        updates[ITEM_OPERATION] = ITEM_KILL
        self.takes_package_service.process_killed_takes_package(original)
        get_resource_service('archive_broadcast').spike_item(original)

    def update(self, id, updates, original):
        """Kill will broadcast kill email notice to all subscriber in the system and then kill the item.

        Kill for multiple items is triggered
        - for all takes and takes_package if one of the take is killed.
        - for broadcast items if master item is killed.
        In case of the multiple items the kill header text will be different but rest
        of the body_html will be same.

        If any other fields needs in the kill template that needs to be based on the item that is being
        killed (not the item that is being actioned on) then modify the article_killed_override.json file'
        For example:
        If there are 2 takes and Take1 is killed and 'body_html' of the take1 is 'Story killed due to legal reason.'

        Take1: {'slugline': 'test1', 'versioncreated': '2016-04-04T00:00:00+0000',
        'dateline': {'text': 'London, PA May 4'}}

        Take2: {'slugline': 'test2', 'versioncreated': '2016-04-05T00:00:00+0000',
        'dateline': {'text': 'London, PA May 5'}}

        Then body_html for Take1 will be:
        'body_html':<p>Please kill story slugged test1 ex London, PA May 4 at 04 May 2016 10:00 AEDT<p>
                    <p>Story killed due to legal reason.</p>

        Then body_html for Take2 will be:
        'body_html':<p>Please kill story slugged test2 ex London, PA May 5 at 05 May 2016 10:00 AEDT<p>
                    <p>Story killed due to legal reason.</p>
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
        self._publish_kill_for_takes(updates_copy, original_copy)
        updated = deepcopy(original)
        updated.update(updates)
        self._process_takes_package(original, updated, updates_copy)
        get_resource_service('archive_broadcast').kill_broadcast(updates_copy, original_copy)

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
        send_article_killed_email(kill_article, recipients, utcnow())

    def _publish_kill_for_takes(self, updates, original):
        """Kill all the takes in a takes package.

        :param updates: Updates of the original document
        :param original: Document to kill
        """
        package = self.takes_package_service.get_take_package(original)
        last_updated = updates.get(config.LAST_UPDATED, utcnow())
        if package:
            for ref in[ref for group in package.get('groups', []) if group['id'] == 'main'
                       for ref in group.get('refs')]:
                if ref[GUID_FIELD] != original[config.ID_FIELD]:
                    updates_data = deepcopy(updates)
                    original_data = super().find_one(req=None, _id=ref[GUID_FIELD])
                    original_data_copy = deepcopy(original_data)
                    self.apply_kill_override(original_data_copy, updates_data)
                    '''
                    Popping out the config.VERSION as Take referenced by original and Take referenced by original_data
                    might have different and if not popped out then it might jump the versions.
                    '''
                    updates_data.pop(config.VERSION, None)
                    self._set_updates(original_data, updates_data, last_updated)
                    self._update_archive(original=original_data, updates=updates_data,
                                         should_insert_into_versions=True)
                    self.update_published_collection(published_item_id=original_data['_id'])

    def kill_item(self, updates, original):
        """Kill the item after applying the template.

        :param dict item: Item
        :param str body_html: body_html of the original item that triggered the kill.
        """
        # apply the kill template
        original_copy = deepcopy(original)
        updates_data = self._apply_kill_template(original_copy)
        updates_data['body_html'] = updates.get('body_html', '')
        # resolve the document version
        resolve_document_version(document=updates_data, resource=ARCHIVE, method='PATCH', latest_doc=original)
        # kill the item
        self.patch(original.get(config.ID_FIELD), updates_data)
        # insert into versions
        insert_into_versions(id_=original[config.ID_FIELD])
