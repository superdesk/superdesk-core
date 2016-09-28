# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import flask
from superdesk.resource import Resource
from superdesk.metadata.utils import extra_response_fields, item_url, aggregations, \
    is_normal_package, elastic_highlight_query
from .common import remove_unwanted, update_state, set_item_expiry, remove_media_files, \
    on_create_item, on_duplicate_item, get_user, update_version, set_sign_off, \
    handle_existing_data, item_schema, validate_schedule, is_item_in_package, update_schedule_settings, \
    ITEM_OPERATION, ITEM_RESTORE, ITEM_UPDATE, ITEM_DESCHEDULE, ARCHIVE as SOURCE, \
    LAST_PRODUCTION_DESK, LAST_AUTHORING_DESK, convert_task_attributes_to_objectId, BROADCAST_GENRE
from superdesk.media.crop import CropService
from flask import current_app as app
from superdesk import get_resource_service
from superdesk.errors import SuperdeskApiError
from eve.versioning import resolve_document_version, versioned_id_field
from superdesk.activity import add_activity, ACTIVITY_CREATE, ACTIVITY_UPDATE, ACTIVITY_DELETE
from eve.utils import parse_request, config, date_to_str, ParsedRequest
from superdesk.services import BaseService
from superdesk.users.services import current_user_has_privilege, is_admin
from superdesk.metadata.item import ITEM_STATE, CONTENT_STATE, CONTENT_TYPE, ITEM_TYPE, EMBARGO, \
    PUBLISH_SCHEDULE, SCHEDULE_SETTINGS, SIGN_OFF
from superdesk.metadata.packages import LINKED_IN_PACKAGES, RESIDREF, SEQUENCE, PACKAGE_TYPE, TAKES_PACKAGE
from apps.common.components.utils import get_component
from apps.item_autosave.components.item_autosave import ItemAutosave
from apps.common.models.base_model import InvalidEtag
from superdesk.etree import get_word_count
from apps.content import push_content_notification, push_expired_notification
from copy import copy, deepcopy
import superdesk
import logging
from apps.common.models.utils import get_model
from apps.item_lock.models.item import ItemModel
from apps.packages import PackageService, TakesPackageService
from .archive_media import ArchiveMediaService
from superdesk.utc import utcnow
import datetime


logger = logging.getLogger(__name__)


def get_subject(doc1, doc2=None):
    for key in ('headline', 'subject', 'slugline'):
        value = doc1.get(key)
        if not value and doc2:
            value = doc2.get(key)
        if value:
            return value


def private_content_filter():
    """Filter out out users private content if this is a user request.

    As private we treat items where user is creator, last version creator,
    or has the item assigned to him atm.

    Also filter out content of stages not visible to current user (if any).
    """
    user = getattr(flask.g, 'user', None)
    if user:
        private_filter = {'should': [
            {'exists': {'field': 'task.desk'}},
            {'term': {'task.user': str(user['_id'])}},
            {'term': {'version_creator': str(user['_id'])}},
            {'term': {'original_creator': str(user['_id'])}},
        ]}

        if 'invisible_stages' in user:
            stages = user.get('invisible_stages')
        else:
            stages = get_resource_service('users').get_invisible_stages_ids(user.get('_id'))

        if stages:
            private_filter['must_not'] = [{'terms': {'task.stage': stages}}]

        return {'bool': private_filter}


class ArchiveVersionsResource(Resource):
    schema = item_schema()
    extra_response_fields = extra_response_fields
    item_url = item_url
    resource_methods = []
    internal_resource = True
    privileges = {'PATCH': 'archive'}


class ArchiveResource(Resource):
    schema = item_schema()
    extra_response_fields = extra_response_fields
    item_url = item_url
    datasource = {
        'search_backend': 'elastic',
        'aggregations': aggregations,
        'es_highlight': elastic_highlight_query,
        'projection': {
            'old_version': 0,
            'last_version': 0
        },
        'default_sort': [('_updated', -1)],
        'elastic_filter': {'bool': {
            'must': {'terms': {'state': ['fetched', 'routed', 'draft', 'in_progress', 'spiked', 'submitted']}},
            'must_not': {'term': {'version': 0}}
        }},
        'elastic_filter_callback': private_content_filter
    }
    etag_ignore_fields = ['highlights', 'broadcast']
    resource_methods = ['GET', 'POST']
    item_methods = ['GET', 'PATCH', 'PUT']
    versioning = True
    privileges = {'POST': SOURCE, 'PATCH': SOURCE, 'PUT': SOURCE}


def update_word_count(doc):
    """Update word count if there was change in content.

    :param doc: created/udpated document
    """
    if doc.get('body_html'):
        doc.setdefault('word_count', get_word_count(doc.get('body_html')))


class ArchiveService(BaseService):
    packageService = PackageService()
    takesService = TakesPackageService()
    mediaService = ArchiveMediaService()

    def on_fetched(self, docs):
        """
        Overriding this to handle existing data in Mongo & Elastic
        """
        self.__enhance_items(docs[config.ITEMS])

    def on_fetched_item(self, doc):
        self.__enhance_items([doc])

    def __enhance_items(self, items):
        for item in items:
            handle_existing_data(item)

        self.takesService.enhance_items_with_takes_packages(items)

    def on_create(self, docs):
        on_create_item(docs)

        for doc in docs:
            if doc.get('body_footer') and is_normal_package(doc):
                raise SuperdeskApiError.badRequestError("Package doesn't support Public Service Announcements")

            doc['version_creator'] = doc['original_creator']
            remove_unwanted(doc)
            update_word_count(doc)
            set_item_expiry({}, doc)

            if doc[ITEM_TYPE] == CONTENT_TYPE.COMPOSITE:
                self.packageService.on_create([doc])

            # Do the validation after Circular Reference check passes in Package Service
            update_schedule_settings(doc, EMBARGO, doc.get(EMBARGO))
            self.validate_embargo(doc)

            if doc.get('media'):
                self.mediaService.on_create([doc])

            # let client create version 0 docs
            if doc.get('version') == 0:
                doc[config.VERSION] = doc['version']

            self._add_desk_metadata(doc, {})

            convert_task_attributes_to_objectId(doc)

    def on_created(self, docs):
        packages = [doc for doc in docs if doc[ITEM_TYPE] == CONTENT_TYPE.COMPOSITE]
        if packages:
            self.packageService.on_created(packages)

        profiles = set()
        for doc in docs:
            subject = get_subject(doc)
            if subject:
                msg = 'added new {{ type }} item about "{{ subject }}"'
            else:
                msg = 'added new {{ type }} item with empty header/title'
            add_activity(ACTIVITY_CREATE, msg,
                         self.datasource, item=doc, type=doc[ITEM_TYPE], subject=subject)

            if doc.get('profile'):
                profiles.add(doc['profile'])

        get_resource_service('content_types').set_used(profiles)
        push_content_notification(docs)

    def on_update(self, updates, original):
        """Runs on archive update.

        Overridden to validate the updates to the article and take necessary actions depending on the updates. In brief,
        it does the following:
            1. Sets state, item operation, version created, version creator, sign off and word count.
            2. Resets Item Expiry
            3. If the request is to de-schedule then checks and de-schedules the associated Takes Package also.
            4. Creates Crops if article is a picture
        """
        user = get_user()
        self._validate_updates(original, updates, user)

        if PUBLISH_SCHEDULE in updates and original[ITEM_STATE] == CONTENT_STATE.SCHEDULED:
            # check if there is a takes package and deschedule the takes package.
            takes_service = TakesPackageService()
            package = takes_service.get_take_package(original)
            if package and package.get(ITEM_STATE) == CONTENT_STATE.SCHEDULED:
                get_resource_service('published').delete_by_article_id(package.get(config.ID_FIELD))
                self.delete_by_article_ids([package.get(config.ID_FIELD)])
                updates[LINKED_IN_PACKAGES] = [package for package in original.get(LINKED_IN_PACKAGES, [])
                                               if package.get(PACKAGE_TYPE) != TAKES_PACKAGE]
            return

        if self.__is_req_for_save(updates):
            update_state(original, updates)

        remove_unwanted(updates)
        self._add_system_updates(original, updates, user)

        self._add_desk_metadata(updates, original)

        if original[ITEM_TYPE] == CONTENT_TYPE.PICTURE:  # create crops
            CropService().create_multiple_crops(updates, original)

        # iterate over associations. Validate and process them if they are stored in database
        if 'associations' in updates:
            for item_name, item_obj in updates.get('associations').items():
                if item_obj and config.ID_FIELD in item_obj:
                    _id = item_obj[config.ID_FIELD]
                    stored_item = self.find_one(req=None, _id=_id)
                    if stored_item:
                        self._validate_updates(stored_item, item_obj, user)
                        if stored_item[ITEM_TYPE] == CONTENT_TYPE.PICTURE:  # create crops
                            CropService().create_multiple_crops(item_obj, stored_item)
                        stored_item.update(item_obj)
                        updates['associations'][item_name] = stored_item

    def on_updated(self, updates, original):
        get_component(ItemAutosave).clear(original['_id'])

        if original[ITEM_TYPE] == CONTENT_TYPE.COMPOSITE:
            self.packageService.on_updated(updates, original)

        CropService().delete_replaced_crop_files(updates, original)

        updated = copy(original)
        updated.update(updates)

        if config.VERSION in updates:
            add_activity(ACTIVITY_UPDATE, 'created new version {{ version }} for item {{ type }} about "{{ subject }}"',
                         self.datasource, item=updated,
                         version=updates[config.VERSION], subject=get_subject(updates, original),
                         type=updated[ITEM_TYPE])

        push_content_notification([updated, original])
        get_resource_service('archive_broadcast').reset_broadcast_status(updates, original)

        if updates.get('profile'):
            get_resource_service('content_types').set_used([updates.get('profile')])

    def on_replace(self, document, original):
        document[ITEM_OPERATION] = ITEM_UPDATE
        remove_unwanted(document)
        user = get_user()
        lock_user = original.get('lock_user', None)
        force_unlock = document.get('force_unlock', False)
        user_id = str(user.get('_id'))
        if lock_user and str(lock_user) != user_id and not force_unlock:
            raise SuperdeskApiError.forbiddenError('The item was locked by another user')
        document['versioncreated'] = utcnow()
        set_item_expiry(document, original)
        document['version_creator'] = user_id
        if force_unlock:
            del document['force_unlock']

    def on_replaced(self, document, original):
        get_component(ItemAutosave).clear(original['_id'])
        add_activity(ACTIVITY_UPDATE, 'replaced item {{ type }} about {{ subject }}',
                     self.datasource, item=original,
                     type=original['type'], subject=get_subject(original))
        push_content_notification([document, original])

    def on_deleted(self, doc):
        if doc[ITEM_TYPE] == CONTENT_TYPE.COMPOSITE:
            self.packageService.on_deleted(doc)

        remove_media_files(doc)

        add_activity(ACTIVITY_DELETE, 'removed item {{ type }} about {{ subject }}',
                     self.datasource, item=doc,
                     type=doc[ITEM_TYPE], subject=get_subject(doc))
        push_expired_notification([doc])

    def replace(self, id, document, original):
        return self.restore_version(id, document, original) or super().replace(id, document, original)

    def find_one(self, req, **lookup):
        item = super().find_one(req, **lookup)

        if item and str(item.get('task', {}).get('stage', '')) in \
                get_resource_service('users').get_invisible_stages_ids(get_user().get('_id')):
            raise SuperdeskApiError.forbiddenError("User does not have permissions to read the item.")

        handle_existing_data(item)
        return item

    def restore_version(self, id, doc, original):
        item_id = id
        old_version = int(doc.get('old_version', 0))
        last_version = int(doc.get('last_version', 0))
        if (not all([item_id, old_version, last_version])):
            return None

        old = get_resource_service('archive_versions').find_one(req=None, _id_document=item_id,
                                                                _current_version=old_version)
        if old is None:
            raise SuperdeskApiError.notFoundError('Invalid version %s' % old_version)

        curr = get_resource_service(SOURCE).find_one(req=None, _id=item_id)
        if curr is None:
            raise SuperdeskApiError.notFoundError('Invalid item id %s' % item_id)

        if curr[config.VERSION] != last_version:
            raise SuperdeskApiError.preconditionFailedError('Invalid last version %s' % last_version)

        old['_id'] = old['_id_document']
        old['_updated'] = old['versioncreated'] = utcnow()
        set_item_expiry(old, doc)
        old.pop('_id_document', None)
        old.pop(SIGN_OFF, None)
        old[ITEM_OPERATION] = ITEM_RESTORE

        resolve_document_version(old, SOURCE, 'PATCH', curr)
        remove_unwanted(old)
        set_sign_off(updates=old, original=curr)

        super().replace(id=item_id, document=old, original=curr)

        old.pop('old_version', None)
        old.pop('last_version', None)

        doc.update(old)
        return item_id

    def duplicate_content(self, original_doc):
        """
        Duplicates the 'original_doc' including it's version history. Copy and Duplicate actions use this method.

        :return: guid of the duplicated article
        """

        if original_doc.get(ITEM_TYPE, '') == CONTENT_TYPE.COMPOSITE:
            for groups in original_doc.get('groups'):
                if groups.get('id') != 'root':
                    associations = groups.get('refs', [])
                    for assoc in associations:
                        if assoc.get(RESIDREF):
                            item, _item_id, _endpoint = self.packageService.get_associated_item(assoc)
                            assoc[RESIDREF] = assoc['guid'] = self.duplicate_content(item)

        return self._duplicate_item(original_doc)

    def _duplicate_item(self, original_doc):
        """Duplicates an item.

        Duplicates the 'original_doc' including it's version history. If the article being duplicated is contained
        in a desk then the article state is changed to Submitted.

        :return: guid of the duplicated article
        """

        new_doc = original_doc.copy()
        self._remove_after_copy(new_doc)
        on_duplicate_item(new_doc)
        resolve_document_version(new_doc, SOURCE, 'PATCH', new_doc)

        if original_doc.get('task', {}).get('desk') is not None and new_doc.get(ITEM_STATE) != CONTENT_STATE.SUBMITTED:
            new_doc[ITEM_STATE] = CONTENT_STATE.SUBMITTED

        convert_task_attributes_to_objectId(new_doc)
        get_model(ItemModel).create([new_doc])
        self._duplicate_versions(original_doc['guid'], new_doc)

        return new_doc['guid']

    def _remove_after_copy(self, copied_item):
        """Removes the properties which doesn't make sense to have for an item after copy.
        """

        del copied_item[config.ID_FIELD]
        del copied_item['guid']
        copied_item.pop(LINKED_IN_PACKAGES, None)
        copied_item.pop(EMBARGO, None)
        copied_item.pop(PUBLISH_SCHEDULE, None)
        copied_item.pop(SCHEDULE_SETTINGS, None)
        copied_item.pop('lock_time', None)
        copied_item.pop('lock_session', None)
        copied_item.pop('lock_user', None)
        copied_item.pop(SIGN_OFF, None)
        copied_item.pop('rewritten_by', None)
        copied_item.pop('rewrite_of', None)
        copied_item.pop('rewrite_sequence', None)
        copied_item.pop('highlights', None)

        task = copied_item.get('task', {})
        task.pop(LAST_PRODUCTION_DESK, None)
        task.pop(LAST_AUTHORING_DESK, None)

    def _duplicate_versions(self, old_id, new_doc):
        """Duplicates version history for an item.

        Duplicates the version history of the article identified by old_id. Each version identifiers are changed
        to have the identifiers of new_doc.

        :param old_id: identifier to fetch version history
        :param new_doc: identifiers from this doc will be used to create version history for the duplicated item.
        """
        resource_def = app.config['DOMAIN']['archive']
        version_id = versioned_id_field(resource_def)
        old_versions = get_resource_service('archive_versions').get(req=None, lookup={'guid': old_id})

        new_versions = []
        for old_version in old_versions:
            old_version[version_id] = new_doc[config.ID_FIELD]
            del old_version[config.ID_FIELD]

            old_version['guid'] = new_doc['guid']
            old_version['unique_name'] = new_doc['unique_name']
            old_version['unique_id'] = new_doc['unique_id']
            old_version['versioncreated'] = utcnow()
            if old_version[config.VERSION] == new_doc[config.VERSION]:
                old_version[ITEM_OPERATION] = new_doc[ITEM_OPERATION]
            new_versions.append(old_version)
        last_version = deepcopy(new_doc)
        last_version['_id_document'] = new_doc['_id']
        del last_version['_id']
        new_versions.append(last_version)
        if new_versions:
            get_resource_service('archive_versions').post(new_versions)

    def update(self, id, updates, original):
        # this needs to here as resolve_nested_documents (in eve) will add the schedule_settings
        if PUBLISH_SCHEDULE in updates and original[ITEM_STATE] == CONTENT_STATE.SCHEDULED:
            self.deschedule_item(updates, original)  # this is an deschedule action

        return super().update(id, updates, original)

    def deschedule_item(self, updates, original):
        """Deschedule an item.

        This operation removed the item from publish queue and published collection.
        :param dict updates: updates for the document
        :param original: original is document.
        """
        updates[ITEM_STATE] = CONTENT_STATE.PROGRESS
        updates[PUBLISH_SCHEDULE] = original[PUBLISH_SCHEDULE]
        updates[SCHEDULE_SETTINGS] = original[SCHEDULE_SETTINGS]
        updates[ITEM_OPERATION] = ITEM_DESCHEDULE
        # delete entry from published repo
        get_resource_service('published').delete_by_article_id(original['_id'])

    def can_edit(self, item, user_id):
        """
        Determines if the user can edit the item or not.
        """
        # TODO: modify this function when read only permissions for stages are implemented
        # TODO: and Content state related checking.

        if not current_user_has_privilege('archive'):
            return False, 'User does not have sufficient permissions.'

        item_location = item.get('task')

        if item_location:
            if item_location.get('desk'):
                if not superdesk.get_resource_service('user_desks').is_member(user_id, item_location.get('desk')):
                    return False, 'User is not a member of the desk.'
            elif item_location.get('user'):
                if not str(item_location.get('user')) == str(user_id):
                    return False, 'Item belongs to another user.'

        return True, ''

    def delete_by_article_ids(self, ids):
        """Remove the content

        :param list ids: list of ids to be removed
        """
        version_field = versioned_id_field(app.config['DOMAIN']['archive_versions'])
        get_resource_service('archive_versions').delete(lookup={version_field: {'$in': ids}})
        super().delete_action({config.ID_FIELD: {'$in': ids}})

    def __is_req_for_save(self, doc):
        """Checks if doc contains req_for_save key.

        Patch of /api/archive is being used in multiple places. This method differentiates from the patch
        triggered by user or not.

        :param dictionary doc: doc to test
        """

        if 'req_for_save' in doc:
            req_for_save = doc['req_for_save']
            del doc['req_for_save']

            return req_for_save == 'true'

        return True

    def validate_embargo(self, item):
        """Validates the embargo of the item.

        Following are checked:
            1. Item can't be a package or a take or a re-write of another story
            2. Publish Schedule and Embargo are mutually exclusive
            3. Always a future date except in case of Corrected and Killed.
        :raises: SuperdeskApiError.badRequestError() if the validation fails
        """

        if item[ITEM_TYPE] != CONTENT_TYPE.COMPOSITE:
            if EMBARGO in item:
                embargo = item.get(SCHEDULE_SETTINGS, {}).get('utc_{}'.format(EMBARGO))
                if embargo:
                    if item.get(PUBLISH_SCHEDULE) or item[ITEM_STATE] == CONTENT_STATE.SCHEDULED:
                        raise SuperdeskApiError.badRequestError("An item can't have both Publish Schedule and Embargo")

                    if (item[ITEM_STATE] not in {CONTENT_STATE.KILLED, CONTENT_STATE.SCHEDULED}) \
                            and embargo <= utcnow():
                        raise SuperdeskApiError.badRequestError("Embargo cannot be earlier than now")

                    package = TakesPackageService().get_take_package(item)
                    if package and package.get(SEQUENCE, 1) > 1:
                        raise SuperdeskApiError.badRequestError("Takes doesn't support Embargo")

                    if item.get('rewrite_of'):
                        raise SuperdeskApiError.badRequestError("Rewrites doesn't support Embargo")

                    if not isinstance(embargo, datetime.date) or not embargo.time():
                        raise SuperdeskApiError.badRequestError("Invalid Embargo")

        elif is_normal_package(item):
            if item.get(EMBARGO):
                raise SuperdeskApiError.badRequestError("A Package doesn't support Embargo")

            self.packageService.check_if_any_item_in_package_has_embargo(item)

    def _validate_updates(self, original, updates, user):
        """Validates updates to the article for the below conditions.

        If any of these conditions are met then exception is raised:
            1.  Is article locked by another user other than the user requesting for update
            2.  Is state of the article is Killed?
            3.  Is user trying to update the package with Public Service Announcements?
            4.  Is user authorized to update unique name of the article?
            5.  Is user trying to update the genre of a broadcast article?
            6.  Is article being scheduled and is in a package?
            7.  Is article being scheduled and schedule timestamp is invalid?
            8.  Does article has valid crops if the article type is a picture?
            9.  Is article a valid package if the article type is a package?
            10. Does article has a valid Embargo?
            11. Make sure that there are no duplicate anpa_category codes in the article.
            12. Make sure there are no duplicate subjects in the upadte

        :raises:
            SuperdeskApiError.forbiddenError()
                - if state of the article is killed or user is not authorized to update unique name or if article is
                  locked by another user
            SuperdeskApiError.badRequestError()
                - if Public Service Announcements are being added to a package or genre is being updated for a
                broadcast, is invalid for scheduling, the updates contain duplicate anpa_category or subject codes
        """
        updated = original.copy()
        updated.update(updates)

        lock_user = original.get('lock_user', None)
        force_unlock = updates.get('force_unlock', False)
        str_user_id = str(user.get(config.ID_FIELD)) if user else None

        if lock_user and str(lock_user) != str_user_id and not force_unlock:
            raise SuperdeskApiError.forbiddenError('The item was locked by another user')

        if original.get(ITEM_STATE) == CONTENT_STATE.KILLED:
            raise SuperdeskApiError.forbiddenError("Item isn't in a valid state to be updated.")

        if updates.get('body_footer') and is_normal_package(original):
            raise SuperdeskApiError.badRequestError("Package doesn't support Public Service Announcements")

        if 'unique_name' in updates and not is_admin(user) \
                and (user['active_privileges'].get('metadata_uniquename', 0) == 0):
            raise SuperdeskApiError.forbiddenError("Unauthorized to modify Unique Name")

        # if broadcast then update to genre is not allowed.
        if original.get('broadcast') and updates.get('genre') and \
                any(genre.get('qcode', '').lower() != BROADCAST_GENRE.lower() for genre in updates.get('genre')):
            raise SuperdeskApiError.badRequestError('Cannot change the genre for broadcast content.')

        if PUBLISH_SCHEDULE in updates or "schedule_settings" in updates:
            if is_item_in_package(original):
                raise SuperdeskApiError.badRequestError(
                    'This item is in a package and it needs to be removed before the item can be scheduled!')

            package = TakesPackageService().get_take_package(original) or {}
            update_schedule_settings(updated, PUBLISH_SCHEDULE, updated.get(PUBLISH_SCHEDULE))

            if updates.get(PUBLISH_SCHEDULE):
                validate_schedule(updated.get(SCHEDULE_SETTINGS, {}).get('utc_{}'.format(PUBLISH_SCHEDULE)),
                                  package.get(SEQUENCE, 1))

            updates[SCHEDULE_SETTINGS] = updated.get(SCHEDULE_SETTINGS, {})

        if original[ITEM_TYPE] == CONTENT_TYPE.PICTURE:
            CropService().validate_multiple_crops(updates, original)
        elif original[ITEM_TYPE] == CONTENT_TYPE.COMPOSITE:
            self.packageService.on_update(updates, original)

        # update the embargo date
        update_schedule_settings(updated, EMBARGO, updated.get(EMBARGO))
        # Do the validation after Circular Reference check passes in Package Service
        self.validate_embargo(updated)
        if EMBARGO in updates or "schedule_settings" in updates:
            updates[SCHEDULE_SETTINGS] = updated.get(SCHEDULE_SETTINGS, {})

        # Ensure that there are no duplicate categories in the update
        category_qcodes = [q['qcode'] for q in updates.get('anpa_category', []) or []]
        if category_qcodes and len(category_qcodes) != len(set(category_qcodes)):
            raise SuperdeskApiError.badRequestError("Duplicate category codes are not allowed")

        # Ensure that there are no duplicate subjects in the update
        subject_qcodes = [q['qcode'] for q in updates.get('subject', []) or []]
        if subject_qcodes and len(subject_qcodes) != len(set(subject_qcodes)):
            raise SuperdeskApiError.badRequestError("Duplicate subjects are not allowed")

    def _add_system_updates(self, original, updates, user):
        """Adds system updates to item.

        As the name suggests, this method adds properties which are derived based on updates sent in the request.
            1. Sets item operation, version created, version creator, sign off and word count.
            2. Resets Item Expiry
        """

        convert_task_attributes_to_objectId(updates)

        updates[ITEM_OPERATION] = ITEM_UPDATE
        updates.setdefault('original_creator', original.get('original_creator'))
        updates['versioncreated'] = utcnow()
        updates['version_creator'] = str(user.get(config.ID_FIELD)) if user else None

        update_word_count(updates)
        update_version(updates, original)

        set_item_expiry(updates, original)
        set_sign_off(updates, original=original)

        # Clear publish_schedule field
        if updates.get(PUBLISH_SCHEDULE) \
                and datetime.datetime.fromtimestamp(0).date() == updates.get(PUBLISH_SCHEDULE).date():
            updates[PUBLISH_SCHEDULE] = None
            updates[SCHEDULE_SETTINGS] = {}

        if updates.get('force_unlock', False):
            del updates['force_unlock']

    def get_expired_items(self, expiry_datetime, invalid_only=False):
        """Get the expired items.

        Where content state is not scheduled and the item matches given parameters

        :param datetime expiry_datetime: expiry datetime
        :param bool invalid_only: True only invalid items
        :return pymongo.cursor: expired non published items.
        """
        query = {
            '$and': [
                {'expiry': {'$lte': date_to_str(expiry_datetime)}},
                {'$or': [
                    {'task.desk': {'$ne': None}},
                    {ITEM_STATE: CONTENT_STATE.SPIKED, 'task.desk': None}
                ]}
            ]
        }

        if invalid_only:
            query['$and'].append({'expiry_status': 'invalid'})
        else:
            query['$and'].append({'expiry_status': {'$ne': 'invalid'}})

        req = ParsedRequest()
        req.max_results = config.MAX_EXPIRY_QUERY_LIMIT
        req.sort = 'expiry,_created'
        return self.get_from_mongo(req=req, lookup=query)

    def _add_desk_metadata(self, updates, original):
        """Populate updates metadata from item desk in case it's set.

        It will only add data which is not set yet on the item.

        :param updates: updates to item that should be saved
        :param original: original item version before update
        """
        return get_resource_service('desks').apply_desk_metadata(updates, original)


class AutoSaveResource(Resource):
    endpoint_name = 'archive_autosave'
    item_url = item_url
    schema = item_schema({'_id': {'type': 'string', 'unique': True}})
    resource_methods = ['POST']
    item_methods = ['GET', 'PUT', 'PATCH', 'DELETE']
    resource_title = endpoint_name
    privileges = {'POST': 'archive', 'PATCH': 'archive', 'PUT': 'archive', 'DELETE': 'archive'}


class ArchiveSaveService(BaseService):
    def create(self, docs, **kwargs):
        if not docs:
            raise SuperdeskApiError.notFoundError('Content is missing')
        req = parse_request(self.datasource)
        try:
            get_component(ItemAutosave).autosave(docs[0]['_id'], docs[0], get_user(required=True), req.if_match)
        except InvalidEtag:
            raise SuperdeskApiError.preconditionFailedError('Client and server etags don\'t match')
        except KeyError:
            raise SuperdeskApiError.badRequestError("Request for Auto-save must have _id")
        return [docs[0]['_id']]


superdesk.workflow_state('in_progress')
superdesk.workflow_action(
    name='save',
    include_states=['draft', 'fetched', 'routed', 'submitted', 'scheduled'],
    privileges=['archive']
)

superdesk.workflow_state('submitted')
superdesk.workflow_action(
    name='move',
    exclude_states=['ingested', 'spiked', 'on-hold', 'published', 'scheduled', 'killed'],
    privileges=['archive']
)
