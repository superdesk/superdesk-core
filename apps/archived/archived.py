# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from operator import itemgetter
from copy import deepcopy
from flask import current_app as app
from eve.utils import config, ParsedRequest
import logging

from eve.versioning import resolve_document_version

from apps.legal_archive.commands import import_into_legal_archive
from apps.legal_archive.resource import LEGAL_PUBLISH_QUEUE_NAME
from apps.publish.content.common import ITEM_KILL
from apps.publish.enqueue import get_enqueue_service
from apps.publish.published_item import published_item_fields, QUEUE_STATE, PUBLISH_STATE, get_content_filter
from apps.packages import PackageService
from superdesk import get_resource_service
from superdesk.errors import SuperdeskApiError
from superdesk.metadata.utils import aggregations
from superdesk.metadata.item import CONTENT_TYPE, ITEM_TYPE, not_analyzed, GUID_FIELD, ITEM_STATE, CONTENT_STATE, \
    PUB_STATUS
from superdesk.metadata.packages import LINKED_IN_PACKAGES, PACKAGE, MAIN_GROUP, RESIDREF
from superdesk.notification import push_notification
from apps.archive.common import get_user, item_schema, is_genre, BROADCAST_GENRE, ITEM_OPERATION, is_item_in_package, \
    insert_into_versions
from apps.archive.archive import SOURCE as ARCHIVE
import superdesk
from superdesk.services import BaseService
from superdesk.resource import Resource
from superdesk.utc import utcnow
from apps.publish.content import KillPublishService, TakeDownPublishService
from flask_babel import _

logger = logging.getLogger(__name__)
PACKAGE_TYPE = 'package_type'
TAKES_PACKAGE = 'takes'
SEQUENCE = 'sequence'
LAST_TAKE = 'last_take'


class ArchivedResource(Resource):
    datasource = {
        'search_backend': 'elastic',
        'aggregations': aggregations,
        'default_sort': [('_updated', -1)],
        'elastic_filter_callback': get_content_filter,
        'projection': {
            'old_version': 0,
            'last_version': 0
        }
    }

    mongo_prefix = 'ARCHIVED'

    extra_fields = published_item_fields.copy()
    # item_id + _current_version will be used fetch archived item.
    extra_fields['archived_id'] = {
        'type': 'string',
        'mapping': not_analyzed
    }

    schema = item_schema(extra_fields)
    resource_methods = ['GET']
    item_methods = ['GET', 'PATCH', 'DELETE']
    privileges = {'PATCH': 'archived', 'DELETE': 'archived'}

    additional_lookup = {
        'url': 'regex("[\w,.:-]+")',
        'field': 'archived_id'
    }


class ArchivedService(BaseService):

    def on_create(self, docs):
        package_service = PackageService()

        for doc in docs:
            doc.pop('lock_user', None)
            doc.pop('lock_time', None)
            doc.pop('lock_action', None)
            doc.pop('lock_session', None)
            doc.pop('highlights', None)
            doc.pop('marked_desks', None)
            doc['archived_id'] = self._get_archived_id(doc.get('item_id'), doc.get(config.VERSION))

            if doc.get(ITEM_TYPE) == CONTENT_TYPE.COMPOSITE:
                for ref in package_service.get_item_refs(doc):
                    ref['location'] = 'archived'

    def validate_delete_action(self, doc, allow_all_types=False):
        """Runs on delete of archive item.

        Overriding to validate the item being killed is actually eligible for kill. Validates the following:
            1. Is item of type Text?
            2. Is item a Broadcast Script?
            3. Does item acts as a Master Story for any of the existing broadcasts?
            4. Is item available in production or part of a normal package?
            5. Is the associated Digital Story is available in production or part of normal package?
            6. If item is a Take then is any take available in production or part of normal package?

        :param doc: represents the article in archived collection
        :type doc: dict
        :param allow_all_types: represents if different types of documents are allowed to be killed
        :type doc: bool
        :raises SuperdeskApiError.badRequestError() if any of the above validation conditions fail.
        """

        bad_req_error = SuperdeskApiError.badRequestError

        id_field = doc[config.ID_FIELD]
        item_id = doc['item_id']

        doc['item_id'] = id_field
        doc[config.ID_FIELD] = item_id

        if not allow_all_types and doc[ITEM_TYPE] != CONTENT_TYPE.TEXT:
            raise bad_req_error(message=_('Only Text articles are allowed to be Killed in Archived repo'))

        if is_genre(doc, BROADCAST_GENRE):
            raise bad_req_error(message=_("Killing of Broadcast Items isn't allowed in Archived repo"))

        if get_resource_service('archive_broadcast').get_broadcast_items_from_master_story(doc, True):
            raise bad_req_error(
                message=_("Can't kill as this article acts as a Master Story for existing broadcast(s)"))

        if get_resource_service(ARCHIVE).find_one(req=None, _id=doc[GUID_FIELD]):
            raise bad_req_error(message=_("Can't Kill as article is still available in production"))

        if not allow_all_types and is_item_in_package(doc):
            raise bad_req_error(message=_("Can't kill as article is part of a Package"))

        takes_package_id = self._get_take_package_id(doc)
        if takes_package_id:
            if get_resource_service(ARCHIVE).find_one(req=None, _id=takes_package_id):
                raise bad_req_error(message=_("Can't Kill as the Digital Story is still available in production"))

            req = ParsedRequest()
            req.sort = '[("%s", -1)]' % config.VERSION
            takes_package = list(self.get(req=req, lookup={'item_id': takes_package_id}))
            if not takes_package:
                raise bad_req_error(message=_('Digital Story of the article not found in Archived repo'))

            takes_package = takes_package[0]
            if not allow_all_types and is_item_in_package(takes_package):
                raise bad_req_error(message=_("Can't kill as Digital Story is part of a Package"))

            for takes_ref in self._get_package_refs(takes_package):
                if takes_ref[RESIDREF] != doc[GUID_FIELD]:
                    if get_resource_service(ARCHIVE).find_one(req=None, _id=takes_ref[RESIDREF]):
                        raise bad_req_error(message=_("Can't Kill as Take(s) are still available in production"))

                    take = list(self.get(req=None, lookup={'item_id': takes_ref[RESIDREF]}))
                    if not take:
                        raise bad_req_error(message=_('One of Take(s) not found in Archived repo'))

                    if not allow_all_types and is_item_in_package(take[0]):
                        raise bad_req_error(message=_("Can't kill as one of Take(s) is part of a Package"))

        doc['item_id'] = item_id
        doc[config.ID_FIELD] = id_field

    def on_delete(self, doc):
        self.validate_delete_action(doc)

    def delete(self, lookup):
        if app.testing and len(lookup) == 0:
            super().delete(lookup)
            return

    def command_delete(self, lookup):
        super().delete(lookup)

    def find_one(self, req, **lookup):
        item = super().find_one(req, **lookup)

        if item and str(item.get('task', {}).get('stage', '')) in \
                get_resource_service('users').get_invisible_stages_ids(get_user().get('_id')):
            raise SuperdeskApiError.forbiddenError(_("User does not have permissions to read the item."))

        return item

    def update(self, id, updates, original):
        """Runs on update of archive item.

        Overriding to handle with Kill/Takedown workflow in the Archived repo:
            1. Check if Article has an associated Digital Story and if Digital Story has more Takes.
               If both Digital Story and more Takes exists then all of them would be killed along with the one requested
            2. If the item is flagged as archived only then it was never created by or published from the system so all
                that needs to be done is to delete it and send an email to all subscribers
            3. For each article being killed do the following:
                i.   Create an entry in archive, archive_versions and published collections.
                ii.  Query the Publish Queue in Legal Archive and find the subscribers who received the article
                     previously and create transmission entries in Publish Queue.
                iii. Change the state of the article to Killed in Legal Archive.
                iv.  Delete all the published versions from Archived.
                v.   Send a broadcast email to all subscribers.
        :param id: primary key of the item to be killed
        :type id: str
        :param updates: updates to be applied on the article before saving
        :type updates: dict
        :param original:
        :type original: dict
        """

        # Step 1
        articles_to_kill = self.find_articles_to_kill({'_id': id})
        logger.info('Fetched articles to kill for id: {}'.format(id))
        articles_to_kill.sort(key=itemgetter(ITEM_TYPE), reverse=True)  # Needed because package has to be inserted last
        kill_service = KillPublishService() if updates.get(ITEM_OPERATION) == ITEM_KILL else TakeDownPublishService()

        updated = original.copy()

        for article in articles_to_kill:
            updates_copy = deepcopy(updates)
            kill_service.apply_kill_override(article, updates_copy)
            updated.update(updates_copy)
            # Step 2, If it is flagged as archived only it has no related items in the system so can be deleted.
            # An email is sent to all subscribers
            if original.get('flags', {}).get('marked_archived_only', False):
                super().delete({'item_id': article['item_id']})
                logger.info('Delete for article: {}'.format(article[config.ID_FIELD]))
                kill_service.broadcast_kill_email(article, updates_copy)
                logger.info('Broadcast kill email for article: {}'.format(article[config.ID_FIELD]))
                continue

            # Step 3(i)
            self._remove_and_set_kill_properties(article, articles_to_kill, updated)
            logger.info('Removing and setting properties for article: {}'.format(article[config.ID_FIELD]))

            # Step 3(ii)
            transmission_details = list(
                get_resource_service(LEGAL_PUBLISH_QUEUE_NAME).get(req=None,
                                                                   lookup={'item_id': article['item_id']}))

            if transmission_details:
                get_enqueue_service(ITEM_KILL).enqueue_archived_kill_item(article, transmission_details)

            article[config.ID_FIELD] = article.pop('item_id', article['item_id'])

            # Step 3(iv)
            super().delete({'item_id': article[config.ID_FIELD]})
            logger.info('Delete for article: {}'.format(article[config.ID_FIELD]))

            # Step 3(i) - Creating entries in published collection
            docs = [article]
            get_resource_service(ARCHIVE).post(docs)
            insert_into_versions(doc=article)
            published_doc = deepcopy(article)
            published_doc[QUEUE_STATE] = PUBLISH_STATE.QUEUED
            get_resource_service('published').post([published_doc])
            logger.info('Insert into archive and published for article: {}'.format(article[config.ID_FIELD]))

            # Step 3(iii)
            import_into_legal_archive.apply_async(countdown=3, kwargs={'item_id': article[config.ID_FIELD]})
            logger.info('Legal Archive import for article: {}'.format(article[config.ID_FIELD]))

            # Step 3(v)
            kill_service.broadcast_kill_email(article, updates_copy)
            logger.info('Broadcast kill email for article: {}'.format(article[config.ID_FIELD]))

    def on_updated(self, updates, original):
        user = get_user()
        push_notification('item:deleted:archived', item=str(original[config.ID_FIELD]),
                          user=str(user.get(config.ID_FIELD)))

    def on_fetched_item(self, doc):
        doc['_type'] = 'archived'

    def _get_archived_id(self, item_id, version):
        return '{}:{}'.format(item_id, version)

    def get_archived_takes_package(self, package_id, take_id, version, include_other_takes=True):
        req = ParsedRequest()
        req.sort = '[("%s", -1)]' % config.VERSION
        take_packages = list(self.get(req=req, lookup={'item_id': package_id}))

        for take_package in take_packages:
            for ref in self._get_package_refs(take_package):
                if ref[RESIDREF] == take_id and (include_other_takes or ref['_current_version'] == version):
                    return take_package

    def find_articles_to_kill(self, lookup, include_other_takes=True):
        """Finds the article to kill.

        If the article is associated with Digital Story then Digital Story will
        also be fetched. If the Digital Story has more takes then all of them would be fetched.

        :param lookup: query to find the main article to be killed
        :type lookup: dict
        :return: list of articles to be killed
        :rtype: list
        """

        archived_doc = self.find_one(req=None, **lookup)
        if not archived_doc:
            return

        req = ParsedRequest()
        req.sort = '[("%s", -1)]' % config.VERSION
        archived_doc = list(self.get(req=req, lookup={'item_id': archived_doc['item_id']}))[0]
        articles_to_kill = [archived_doc]
        takes_package_id = self._get_take_package_id(archived_doc)
        if takes_package_id:
            takes_package = self.get_archived_takes_package(takes_package_id,
                                                            archived_doc['item_id'],
                                                            archived_doc['_current_version'],
                                                            include_other_takes)
            articles_to_kill.append(takes_package)

            if include_other_takes:
                for takes_ref in self._get_package_refs(takes_package):
                    if takes_ref[RESIDREF] != archived_doc[GUID_FIELD]:
                        take = list(self.get(req=req, lookup={'item_id': takes_ref[RESIDREF]}))[0]
                        articles_to_kill.append(take)

        return articles_to_kill

    def _remove_and_set_kill_properties(self, article, articles_to_kill, updates):
        """Removes the irrelevant properties from the given article and sets the properties for kill operation.

        :param article: article from the archived repo
        :type article: dict
        :param articles_to_kill: list of articles which were about to kill from dusty archive
        :type articles_to_kill: list
        :param updates: updates to be applied on the article before saving
        :type updates: dict
        """

        article.pop('archived_id', None)
        article.pop('_type', None)
        article.pop('_links', None)
        article.pop('queue_state', None)
        article.pop(config.ETAG, None)

        for field in ['headline', 'abstract', 'body_html']:
            article[field] = updates.get(field, article.get(field, ''))

        article[ITEM_STATE] = CONTENT_STATE.KILLED if updates[ITEM_OPERATION] == ITEM_KILL else CONTENT_STATE.RECALLED
        article[ITEM_OPERATION] = updates[ITEM_OPERATION]
        article['pubstatus'] = PUB_STATUS.CANCELED
        article[config.LAST_UPDATED] = utcnow()

        user = get_user()
        article['version_creator'] = str(user[config.ID_FIELD])

        resolve_document_version(article, ARCHIVE, 'PATCH', article)

        if article[ITEM_TYPE] == CONTENT_TYPE.COMPOSITE:
            package_service = PackageService()
            item_refs = package_service.get_item_refs(article)
            for ref in item_refs:
                item_in_package = [item for item in articles_to_kill
                                   if item.get('item_id', item.get(config.ID_FIELD)) == ref[RESIDREF]]
                ref['location'] = ARCHIVE
                ref[config.VERSION] = item_in_package[0][config.VERSION]

    def _get_take_package_id(self, item):
        """Checks if the item is in a 'takes' package and returns the package id

        :return: _id of the package or None
        """
        takes_package = [package.get(PACKAGE) for package in item.get(LINKED_IN_PACKAGES, [])
                         if package.get(PACKAGE_TYPE) == TAKES_PACKAGE]
        if len(takes_package) > 1:
            message = 'Multiple takes found for item: {0}'.format(item[config.ID_FIELD])
            logger.error(message)
        return takes_package[0] if takes_package else None

    def _get_package_refs(self, package):
        """Get refs from the takes package

        :param dict package: takes package
        :return: return refs from the takes package. If not takes package or no refs found then None
        """
        refs = None
        if package:
            groups = package.get('groups', [])
            refs = next((group.get('refs') for group in groups if group['id'] == MAIN_GROUP), None)

        return refs


superdesk.privilege(name='archived', label='Archive Management', description='User can remove items from the archived')
