# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license
import json
import itertools

import superdesk
from flask import current_app as app

from superdesk import get_resource_service
from superdesk.errors import SuperdeskApiError
from superdesk.resource import Resource
from superdesk import config
from superdesk.utils import SuperdeskBaseEnum
from bson.objectid import ObjectId
from superdesk.services import BaseService
from superdesk.notification import push_notification
from superdesk.activity import add_activity, ACTIVITY_UPDATE
from superdesk.metadata.item import FAMILY_ID
from eve.utils import ParsedRequest
from superdesk.utils import ListCursor
from flask_babel import _


class DeskTypes(SuperdeskBaseEnum):
    authoring = 'authoring'
    production = 'production'


desks_schema = {
    'name': {
        'type': 'string',
        'required': True,
        'nullable': False,
        'empty': False,
        'iunique': True
    },
    'description': {
        'type': 'string'
    },
    'members': {
        'type': 'list',
        'schema': {
            'type': 'dict',
            'schema': {
                'user': Resource.rel('users', True)
            }
        }
    },
    'incoming_stage': Resource.rel('stages', True),
    'working_stage': Resource.rel('stages', True),
    'content_expiry': {
        'type': 'integer'
    },
    'source': {
        'type': 'string'
    },
    'monitoring_settings': {
        'type': 'list',
        'schema': {
            'type': 'dict',
            'schema': {
                '_id': {
                    'type': 'string',
                    'required': True
                },
                'type': {
                    'type': 'string',
                    'allowed': ['search', 'stage', 'scheduledDeskOutput', 'deskOutput', 'personal', 'sentDeskOutput'],
                    'required': True
                },
                'max_items': {
                    'type': 'integer',
                    'required': True
                }
            }
        }
    },
    'desk_type': {
        'type': 'string',
        'default': DeskTypes.authoring.value,
        'allowed': DeskTypes.values()
    },
    'desk_metadata': {
        'type': 'dict',
    },

    'content_profiles': {
        'type': 'dict',
    },

    'desk_language': {
        'type': 'string'
    },

    'monitoring_default_view': {
        'type': 'string',
        'allowed': ['', 'list', 'swimlane', 'photogrid'],
        'required': False
    },

    'default_content_profile': Resource.rel('content_types', type='string', nullable=True),
    'default_content_template': Resource.rel('content_templates', nullable=True),
    # name of a Slack channel that may be associated with the desk
    'slack_channel_name': {
        'type': 'string'
    },

    # desk prefered vocabulary items
    'preferred_cv_items': {
        'type': 'dict',
    },
    # if the preserve_published_content is set to true then the content on this won't be expired
    'preserve_published_content': {
        'type': 'boolean',
        'required': False,
        'default': False
    }
}


def init_app(app):
    endpoint_name = 'desks'
    service = DesksService(endpoint_name, backend=superdesk.get_backend())
    DesksResource(endpoint_name, app=app, service=service)
    endpoint_name = 'user_desks'
    service = UserDesksService(endpoint_name, backend=superdesk.get_backend())
    UserDesksResource(endpoint_name, app=app, service=service)
    endpoint_name = 'sluglines'
    service = SluglineDeskService(endpoint_name, backend=superdesk.get_backend())
    SluglineDesksResource(endpoint_name, app=app, service=service)


superdesk.privilege(name='desks', label='Desk Management', description='User can manage desks.')


class DesksResource(Resource):
    schema = desks_schema
    privileges = {'POST': 'desks', 'PATCH': 'desks', 'DELETE': 'desks'}
    datasource = {'default_sort': [('name', 1)]}
    mongo_indexes = {
        'name_1': ([('name', 1)], {'unique': True}),
    }


class DesksService(BaseService):
    notification_key = 'desk'

    def create(self, docs, **kwargs):
        """Creates new desk.

        Overriding to check if the desk being created has Working and Incoming Stages. If not then Working and Incoming
        Stages would be created and associates them with the desk and desk with the Working and Incoming Stages.
        Also sets desk_type.

        :return: list of desk id's
        """

        for desk in docs:
            stages_to_be_linked_with_desk = []
            stage_service = superdesk.get_resource_service('stages')
            self._ensure_unique_members(desk)

            if desk.get('content_expiry') == 0:
                desk['content_expiry'] = app.settings['CONTENT_EXPIRY_MINUTES']

            if 'working_stage' not in desk:
                stages_to_be_linked_with_desk.append('working_stage')
                stage_id = stage_service.create_working_stage()
                desk['working_stage'] = stage_id[0]

            if 'incoming_stage' not in desk:
                stages_to_be_linked_with_desk.append('incoming_stage')
                stage_id = stage_service.create_incoming_stage()
                desk['incoming_stage'] = stage_id[0]

            desk.setdefault('desk_type', DeskTypes.authoring.value)
            super().create([desk], **kwargs)
            for stage_type in stages_to_be_linked_with_desk:
                stage_service.patch(desk[stage_type], {'desk': desk[config.ID_FIELD]})

        return [doc[config.ID_FIELD] for doc in docs]

    def on_created(self, docs):
        for doc in docs:
            push_notification(self.notification_key, created=1, desk_id=str(doc.get(config.ID_FIELD)))
            get_resource_service('users').update_stage_visibility_for_users()

    def on_update(self, updates, original):
        if updates.get('content_expiry') == 0:
            updates['content_expiry'] = None

        self._ensure_unique_members(updates)

        if updates.get('desk_type') and updates.get('desk_type') != original.get('desk_type', ''):
            archive_versions_query = {
                '$or': [
                    {'task.last_authoring_desk': str(original[config.ID_FIELD])},
                    {'task.last_production_desk': str(original[config.ID_FIELD])}
                ]
            }

            items = superdesk.get_resource_service('archive_versions').get(req=None, lookup=archive_versions_query)
            if items and items.count():
                raise SuperdeskApiError.badRequestError(
                    message=_('Cannot update Desk Type as there are article(s) referenced by the Desk.'))

    def _ensure_unique_members(self, doc):
        """Ensure the members are unique"""
        if doc.get('members'):
            # ensuring that members list is unique
            doc['members'] = [{'user': user} for user in {member.get('user') for member in doc.get('members')}]

    def on_updated(self, updates, original):
        self.__send_notification(updates, original)

    def on_delete(self, desk):
        """Runs on desk delete.

        Overriding to prevent deletion of a desk if the desk meets one of the below conditions:
            1. The desk isn't assigned as a default desk to user(s)
            2. The desk has no content
            3. The desk is associated with routing rule(s)
        """

        as_default_desk = superdesk.get_resource_service('users').get(req=None, lookup={'desk': desk[config.ID_FIELD]})
        if as_default_desk and as_default_desk.count():
            raise SuperdeskApiError.preconditionFailedError(
                message=_('Cannot delete desk as it is assigned as default desk to user(s).'))

        routing_rules_query = {
            '$or': [
                {'rules.actions.fetch.desk': desk[config.ID_FIELD]},
                {'rules.actions.publish.desk': desk[config.ID_FIELD]}
            ]
        }
        routing_rules = superdesk.get_resource_service('routing_schemes').get(req=None, lookup=routing_rules_query)
        if routing_rules and routing_rules.count():
            raise SuperdeskApiError.preconditionFailedError(
                message=_('Cannot delete desk as routing scheme(s) are associated with the desk'))

        archive_versions_query = {
            '$or': [
                {'task.desk': str(desk[config.ID_FIELD])},
                {'task.last_authoring_desk': str(desk[config.ID_FIELD])},
                {'task.last_production_desk': str(desk[config.ID_FIELD])}
            ]
        }

        items = superdesk.get_resource_service('archive_versions').get(req=None, lookup=archive_versions_query)
        if items and items.count():
            raise SuperdeskApiError.preconditionFailedError(
                message=_('Cannot delete desk as it has article(s) or referenced by versions of the article(s).'))

    def add_member(self, desk_id, user_id):
        desk = self.find_one(req=None, _id=desk_id)
        if not desk:
            raise ValueError('desk "{}" not found'.format(desk_id))
        members = desk.get('members', [])
        members.append({'user': user_id})
        updates = {'members': members}
        self.on_update(updates, desk)
        self.system_update(desk['_id'], updates, desk)

    def delete(self, lookup):
        """
        Overriding to delete stages before deleting a desk
        """

        superdesk.get_resource_service('stages').delete(lookup={'desk': lookup.get(config.ID_FIELD)})
        super().delete(lookup)

    def on_deleted(self, doc):
        desk_user_ids = [str(member['user']) for member in doc.get('members', [])]
        push_notification(self.notification_key,
                          deleted=1,
                          user_ids=desk_user_ids,
                          desk_id=str(doc.get(config.ID_FIELD)))

    def __compare_members(self, original, updates):
        original_members = set([member['user'] for member in original])
        updates_members = set([member['user'] for member in updates])
        added = updates_members - original_members
        removed = original_members - updates_members
        return added, removed

    def __send_notification(self, updates, desk):
        desk_id = desk[config.ID_FIELD]

        if 'members' in updates:
            added, removed = self.__compare_members(desk.get('members', {}), updates['members'])
            if len(removed) > 0:
                push_notification('desk_membership_revoked',
                                  updated=1,
                                  user_ids=[str(item) for item in removed],
                                  desk_id=str(desk_id))

            for added_user in added:
                user = superdesk.get_resource_service('users').find_one(req=None, _id=added_user)
                activity = add_activity(ACTIVITY_UPDATE,
                                        'user {{user}} has been added to desk {{desk}}: Please re-login.',
                                        self.datasource, notify=added, can_push_notification=False,
                                        user=user.get('username'), desk=desk.get('name'))
                push_notification('activity', _dest=activity['recipients'])

            get_resource_service('users').update_stage_visibility_for_users()
        else:
            push_notification(self.notification_key, updated=1, desk_id=str(desk.get(config.ID_FIELD)))

    def apply_desk_metadata(self, updates, original):
        """Apply desk metadata in case it was set in updates and metadata is not set yet on item.

        :param updates: updates to item that should be saved
        :param original: original item version before update
        """
        desk_id = updates.get('task', {}).get('desk', {})
        if not desk_id:
            return
        desk = self.find_one(req=None, _id=desk_id)
        if not desk:
            return
        for key, val in desk.get('desk_metadata', {}).items():
            if key not in updates and key not in original:
                updates[key] = val

    def get_desk_name(self, desk_id):
        """Return the item desk.

        :param desk_id:
        :return dict: desk document
        """
        desk_name = ''
        desk = get_resource_service('desks').find_one(req=None, _id=desk_id)
        if desk:
            desk_name = desk.get('name') or ''

        return desk_name

    def get(self, req, lookup):
        desks = tuple(super().get(req, lookup))

        members_set = set()
        db_users = app.data.mongo.pymongo('users').db['users']

        # find display_name from the users document for each member in desks document
        for desk in desks:
            if 'members' in desk:
                users = tuple(db_users.find({
                    '_id': {'$in': [member['user'] for member in desk['members']]}},
                    {'display_name': 1}
                ))
                members_set |= {(m['_id'], m['display_name']) for m in users}

        if members_set:
            members_list = list(members_set)
            members_list.sort(key=lambda k: k[1].lower())
            sorted_members_ids = tuple(m[0] for m in members_list)

            # sort the members of each desk according to ordered_dict
            for desk in desks:
                if 'members' in desk:
                    # remove members which don't exist in db
                    desk['members'] = [member for member in desk['members'] if member['user'] in sorted_members_ids]
                    # sort member in desk
                    desk['members'].sort(key=lambda x: sorted_members_ids.index(x['user']))

        return ListCursor(desks)


class UserDesksResource(Resource):
    url = 'users/<regex("[a-f0-9]{24}"):user_id>/desks'
    resource_title = 'user_desks'
    schema = desks_schema
    datasource = {'source': 'desks', 'default_sort': [('name', 1)]}
    resource_methods = ['GET']


class UserDesksService(BaseService):

    def get(self, req, lookup):
        if lookup.get('user_id'):
            lookup['members.user'] = ObjectId(lookup['user_id'])
            del lookup['user_id']
        return super().get(req, lookup)

    def is_member(self, user_id, desk_id):
        # desk = list(self.get(req=None, lookup={'members.user':ObjectId(user_id), '_id': ObjectId(desk_id)}))
        return len(list(self.get(req=None, lookup={'members.user': ObjectId(user_id), '_id': ObjectId(desk_id)}))) > 0


class SluglineDesksResource(Resource):

    url = 'desks/<regex("[a-f0-9]{24}"):desk_id>/sluglines'
    datasource = {'source': 'published',
                  'search_backend': 'elastic',
                  'default_sort': [('slugline.phrase', 1), ("versioncreated", 0)],
                  'elastic_filter': {"and": [{"range": {"versioncreated": {"gte": "now-24H"}}},
                                             {"term": {"last_published_version": True}},
                                             {"term": {"type": "text"}}
                                             ]}}
    resource_methods = ['GET']
    item_methods = []
    schema = {
        'place': {'type': 'string'},
        'items': {'type': 'list'},
    }


class SluglineDeskService(BaseService):
    SLUGLINE = 'slugline'
    OLD_SLUGLINES = 'old_sluglines'
    VERSION_CREATED = 'versioncreated'
    HEADLINE = 'headline'
    NAME = 'name'
    PLACE = 'place'
    GROUP = 'group'

    def _get_slugline_with_legal(self, article):
        """If the article is set to be legal adds 'Legal:' prefix for slugline.

        :param article:
        :return:
        """
        is_legal = article.get('flags', {}).get('marked_for_legal', False)
        if is_legal:
            return '{}: {}'.format('Legal', article.get(self.SLUGLINE, ''))
        else:
            return article.get(self.SLUGLINE, '')

    def get(self, req, lookup):
        """Return desk item summary.

        Given the desk the function will return a summary of the sluglines and headlines published from that
        desk in the last 24 hours. Domestic items are grouped together, rest of the world items are group
        by their place names.

        :param req:
        :param lookup:
        :return:
        """
        lookup['task.desk'] = lookup['desk_id']
        lookup.pop('desk_id')
        req.max_results = 1000
        desk_items = super().get(req, lookup)

        # domestic docs
        docs = []
        # rest of the world docs
        row_docs = []
        for item in desk_items:
            slugline = self._get_slugline_with_legal(item)
            headline = item.get(self.HEADLINE)
            versioncreated = item.get(self.VERSION_CREATED)
            placename = 'Domestic'
            # Determine if the item is either domestic or rest of the world
            place = next((place for place in (item.get('place') or [])), None)

            if place and place.get(self.GROUP) == 'Rest Of World':
                row = True
                placename = place.get(self.NAME, 'Domestic')
            else:
                row = False
            # Find if there are other sluglines in this items family
            newer, older_slugline = self._find_other_sluglines(item.get(FAMILY_ID), slugline,
                                                               item.get(self.VERSION_CREATED),
                                                               lookup['task.desk'])
            # there are no newer sluglines than the current one
            if not newer:
                if row:
                    self._add_slugline_to_places(row_docs, placename, slugline, headline, older_slugline,
                                                 versioncreated)
                else:
                    self._add_slugline_to_places(docs, placename, slugline, headline, older_slugline, versioncreated)

        docs.extend(row_docs)
        items = []

        # group by place and sort all items of a place by versioncreated.
        for key, group in itertools.groupby(docs, lambda x: x['name']):
            items.append({'place': key, 'items': sorted(group, key=lambda k: k['versioncreated'], reverse=True)})

        desk_items.docs = items
        return desk_items

    def _add_slugline_to_places(self, places, placename, slugline, headline, old_sluglines, versioncreated):
        """Add slugline to places.

        Append a dictionary to the list, with place holders for the place name and slugline if they are already
        present.

        :param places:
        :param placename:
        :param slugline:
        :param headline:
        :param is_legal:
        :param old_sluglines:
        :param versioncreated:
        :return:
        """
        places.append({self.NAME: placename,
                       self.SLUGLINE: slugline if not any(self._get_slugline_with_legal(p).lower() == slugline.lower()
                                                          for p in places) else '-',
                       self.HEADLINE: headline,
                       self.OLD_SLUGLINES: old_sluglines,
                       self.VERSION_CREATED: versioncreated})

    def _find_other_sluglines(self, family_id, slugline, versioncreated, desk_id):
        """Find other sluglines.

        This function given a family_id will return a tuple with the first value true if there is
         a more recent story in the family, the second value in the tuple will be a list of any sluglines
         that might exist for the family that are different to the one passed.

        :param family_id:
        :param slugline:
        :param versioncreated:
        :param desk_id:
        :return: A tuple as described above
        """
        older_sluglines = []
        req = ParsedRequest()
        query = {
            'query': {
                'filtered': {
                    'filter': {
                        'and': [
                            {'term': {'family_id': family_id}},
                            {'term': {'task.desk': desk_id}},
                        ]
                    }
                }
            }
        }
        req.args = {'source': json.dumps(query), 'aggregations': 0}
        family = superdesk.get_resource_service('published').get(req=req, lookup=None)
        for member in family:
            member_slugline = self._get_slugline_with_legal(member)
            if member_slugline.lower() != slugline.lower():
                if member.get('versioncreated') < versioncreated:
                    if member_slugline not in older_sluglines:
                        older_sluglines.append(member_slugline)
                else:
                    return (True, [])
        return (False, older_sluglines)


def remove_profile_from_desks(item):
    """Removes the profile data from desks that are using the profile

    :param item: deleted content profile
    """
    req = ParsedRequest()
    desks = list(superdesk.get_resource_service('desks').get(req=req, lookup={}))
    for desk in desks:
        if desk.get('default_content_profile') == str(item.get(config.ID_FIELD)):
            desk['default_content_profile'] = None
            superdesk.get_resource_service('desks').patch(desk[config.ID_FIELD], desk)
