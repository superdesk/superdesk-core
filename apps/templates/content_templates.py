# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2015 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import re
import superdesk
import logging
from flask import render_template_string, current_app as app
from copy import deepcopy
from superdesk.services import BaseService
from superdesk import Resource, Service, config, get_resource_service
from superdesk.utils import SuperdeskBaseEnum, plaintext_filter
from superdesk.resource import build_custom_hateoas
from superdesk.utc import utcnow, local_to_utc, utc_to_local
from superdesk.errors import SuperdeskApiError
from superdesk.metadata.item import metadata_schema, ITEM_STATE, CONTENT_STATE
from superdesk.celery_app import celery
from apps.tasks import apply_onstage_rule
from apps.archive.common import ARCHIVE, CUSTOM_HATEOAS, item_schema, format_dateline_to_locmmmddsrc, \
    insert_into_versions, ARCHIVE_SCHEMA_FIELDS
from apps.auth import get_user

from superdesk.lock import lock, unlock
from superdesk.celery_task_utils import get_lock_id
from croniter import croniter
from datetime import datetime
from flask_babel import _
from superdesk.notification import push_notification

CONTENT_TEMPLATE_RESOURCE = 'content_templates'
CONTENT_TEMPLATE_PRIVILEGE = CONTENT_TEMPLATE_RESOURCE
TEMPLATE_FIELDS = {'template_name', 'template_type', 'schedule', 'type', 'state',
                   'last_run', 'next_run', 'template_desks', 'schedule_desk', 'schedule_stage',
                   config.ID_FIELD, config.LAST_UPDATED, config.DATE_CREATED,
                   config.ETAG, 'task'}
KILL_TEMPLATE_NOT_REQUIRED_FIELDS = ['schedule', 'dateline', 'template_desks', 'schedule_desk',
                                     'schedule_stage']
PLAINTEXT_FIELDS = {'headline'}


logger = logging.getLogger(__name__)


class TemplateType(SuperdeskBaseEnum):
    KILL = 'kill'
    CREATE = 'create'
    HIGHLIGHTS = 'highlights'


def get_schema():
    schema = deepcopy(metadata_schema)
    schema['target_types'] = ARCHIVE_SCHEMA_FIELDS.get('target_types')
    schema['target_regions'] = ARCHIVE_SCHEMA_FIELDS.get('target_regions')
    schema['target_subscribers'] = ARCHIVE_SCHEMA_FIELDS.get('target_subscribers')
    return schema


def get_next_run(schedule, now_utc=None):
    """Get next run time based on schedule.

    Schedule is day of week and time.

    :param dict schedule: dict with `day_of_week` and `create_at` params
    :param now_utc
    :return datetime
    """
    if not schedule.get('is_active', False):
        return None

    if now_utc is None:
        now_utc = utcnow()

    now_utc = now_utc.replace(second=0)

    # Derive the first cron_list entry from the create_at and day_of_week
    if 'create_at' in schedule and 'cron_list' not in schedule:
        time = schedule.get('create_at').split(':')
        cron_days = ','.join(schedule.get('day_of_week', '*')) if len(schedule.get('day_of_week')) else '*'
        cron_entry = '{} {} * * {}'.format(time[1], time[0], cron_days)
        schedule['cron_list'] = [cron_entry]
        schedule.pop('create_at', None)

    # adjust current time to the schedule's timezone
    tz_name = schedule.get('time_zone', 'UTC')
    if tz_name != 'UTC':
        current_local_datetime = utc_to_local(tz_name, now_utc)  # convert utc to local time
        cron = croniter(schedule.get('cron_list')[0], current_local_datetime)
        next_run = local_to_utc(tz_name, cron.get_next(datetime))
        for cron_entry in schedule.get('cron_list'):
            next_candidate = local_to_utc(tz_name, croniter(cron_entry, current_local_datetime).get_next(datetime))
            if next_candidate < next_run:
                next_run = next_candidate
    else:
        cron = croniter(schedule.get('cron_list')[0], now_utc)
        next_run = cron.get_next(datetime)
        for cron_entry in schedule.get('cron_list'):
            next_candidate = croniter(cron_entry, now_utc).get_next(datetime)
            if next_candidate < next_run:
                next_run = next_candidate

    return next_run


def push_template_notification(docs, event='template:update'):
    user = get_user()
    template_desks = set()

    for doc in docs:
        if doc.get('template_desks'):
            template_desks.update([str(template) for template in doc.get('template_desks')])

    push_notification(event, user=str(user.get(config.ID_FIELD, '')), desks=list(template_desks))


class ContentTemplatesResource(Resource):
    schema = {
        'data': {
            'type': 'dict',
            'schema': get_schema(),
        },

        'template_name': {
            'type': 'string',
            'unique_template': True,
            'required': True,
        },

        'template_type': {
            'type': 'string',
            'required': True,
            'allowed': TemplateType.values(),
            'default': TemplateType.CREATE.value,
        },

        'template_desks': {
            'type': 'list',
            'required': False,
            'nullable': True,
            'schema': Resource.rel('desks', embeddable=False, nullable=True)
        },

        'schedule_desk': Resource.rel('desks', embeddable=False, nullable=True),

        'schedule_stage': Resource.rel('stages', embeddable=False, nullable=True),

        'schedule': {'type': 'dict', 'schema': {
            'is_active': {'type': 'boolean'},
            'create_at': {'type': 'string'},
            # List of cron expressions that determine the times items should be created.
            'cron_list': {'type': 'list', 'required': False, 'nullable': True,
                          'schema': {'type': 'string'}},
            'day_of_week': {'type': 'list'},
            'time_zone': {
                'type': 'string',
                'nullable': True
            }
        }},

        'last_run': {'type': 'datetime', 'readonly': True},
        'next_run': {'type': 'datetime', 'readonly': True},

        'user': Resource.rel('users'),
        'is_public': {'type': 'boolean', 'unique_template': True, 'default': False},
    }

    additional_lookup = {
        'url': 'regex("[\w]+")',
        'field': 'template_name'
    }

    resource_methods = ['GET', 'POST']
    item_methods = ['GET', 'PATCH', 'DELETE']
    privileges = {'POST': CONTENT_TEMPLATE_PRIVILEGE,
                  'PATCH': CONTENT_TEMPLATE_PRIVILEGE,
                  'DELETE': CONTENT_TEMPLATE_PRIVILEGE}


class ContentTemplatesService(BaseService):

    def on_create(self, docs):
        for doc in docs:
            doc['template_name'] = doc['template_name'].lower().strip()
            if doc.get('schedule'):
                doc['next_run'] = get_next_run(doc.get('schedule'))

            if doc.get('template_type') == TemplateType.KILL.value and \
                    any(key for key in doc.keys() if key in KILL_TEMPLATE_NOT_REQUIRED_FIELDS):
                raise SuperdeskApiError.badRequestError(
                    message=_("Invalid kill template. {fields} are not allowed").format(
                        fields=', '.join(KILL_TEMPLATE_NOT_REQUIRED_FIELDS)))
            if doc.get('template_type') == TemplateType.KILL.value:
                self._validate_kill_template(doc)
            if get_user():
                doc.setdefault('user', get_user()[config.ID_FIELD])
            self._validate_template_desks(doc)

    def on_created(self, docs):
        push_template_notification(docs)

    def on_update(self, updates, original):
        if updates.get('template_type') and updates.get('template_type') != original.get('template_type') and \
           updates.get('template_type') == TemplateType.KILL.value:
            self._validate_kill_template(updates)
            self._process_kill_template(updates)

        if updates.get('schedule'):
            original_schedule = deepcopy(original.get('schedule', {}))
            original_schedule.update(updates.get('schedule'))
            updates['next_run'] = get_next_run(original_schedule)
        self._validate_template_desks(updates, original)

        profile_id = updates.get('data', {}).get('profile')
        if profile_id and str(profile_id) != str(original.get('data', {}).get('profile', '')):
            # if profile is changed remove unnecessary fields from template
            original_template = deepcopy(original)
            original_template.update(updates)
            profile = get_resource_service('content_types').find_one(req=None, _id=profile_id)
            data, _ = self._reset_fields(original_template, profile)
            updates['data'] = data

    def on_updated(self, updates, original):
        push_template_notification([updates, original])

    def on_fetched(self, docs):
        self.enhance_items(docs[config.ITEMS])

    def on_fetched_item(self, doc):
        self.enhance_items([doc])

    def enhance_items(self, items):
        for item in items:
            self.handle_existing_data(item)

    def handle_existing_data(self, item):
        schedule = item.get('schedule')
        if schedule and 'cron_list' not in schedule and 'create_at' in schedule:
            time = schedule.get('create_at').split(':')
            cron_days = ','.join(schedule.get('day_of_week', '*')) if len(schedule.get('day_of_week')) else '*'
            cron_entry = '{} {} * * {}'.format(time[1], time[0], cron_days)
            schedule['cron_list'] = [cron_entry]
            schedule.pop('create_at', None)

    def on_delete(self, doc):
        if doc.get('template_type') == TemplateType.KILL.value:
            raise SuperdeskApiError.badRequestError(_('Kill templates can not be deleted.'))

    def on_deleted(self, doc):
        push_template_notification([doc])

    def get_scheduled_templates(self, now):
        """Get the template by schedule

        :param datetime now:
        :return MongoCursor:
        """
        query = {'next_run': {'$lte': now}, 'schedule.is_active': True}
        return self.find(query)

    def get_templates_by_profile_id(self, profile_id):
        """Get all templates by profile id"""
        templates = self.get(req=None, lookup=None)
        return [t for t in templates if str(t.get('data', {}).get('profile', '')) == str(profile_id)]

    def update_template_profile(self, updates, profile_id, templates=None):
        """
        Finds the templates that are referencing the given
        content profile an clears the disabled fields
        :param updates: changed data for the content profile
        :param profile_id: id of the profile in string
        :param templates: list of templates to process
        """
        if not templates:
            templates = list(self.get_templates_by_profile_id(profile_id))

        for template in templates:
            data, processed = self._reset_fields(template, updates)
            if processed:
                self.patch(template.get(config.ID_FIELD), {'data': data})

    def _reset_fields(self, template, profile_data):
        """
        Removes fields from template which is disabled or doesn't exist in profile
        """
        fields_to_keep = ['profile', 'type', 'flags', 'format', 'pubstatus', 'language', 'usageterms', 'company_codes',
                          'keywords', 'target_regions', 'target_types', 'target_subscribers']
        data = deepcopy(template.get('data', {}))
        schema = profile_data.get('schema', {})
        processed = False

        # Reset fields that are disabled or doesn't exist in content profile
        fields_to_remove = []
        for field, params in data.items():
            if field not in schema or not schema.get(field) or \
                    not schema.get(field, {}).get('enabled', True):
                fields_to_remove.append(field)

        for field in fields_to_remove:
            if field not in fields_to_keep:
                if field in metadata_schema:
                    if metadata_schema.get(field, {}).get('nullable'):
                        data[field] = None
                    else:
                        if metadata_schema.get(field, {}).get('type') == 'list':
                            data[field] = []
                        if metadata_schema.get(field, {}).get('type') == 'string':
                            data[field] = ''
                        if metadata_schema.get(field, {}).get('type') == 'integer':
                            data[field] = 0
                        if metadata_schema.get(field, {}).get('type') == 'dict':
                            data[field] = {}
                else:
                    data[field] = None
                processed = True

        return data, processed

    def get_template_by_name(self, template_name):
        """Get the template by name

        :param str template_name: template name
        :return dict: template
        """
        query = {'template_name': re.compile('^{}$'.format(template_name), re.IGNORECASE)}
        return self.find_one(req=None, **query)

    def _validate_kill_template(self, doc):
        """
        Validates input values for kill templates
        """
        if doc.get('template_type') != TemplateType.KILL.value:
            return

        if doc.get('template_desks'):
            raise SuperdeskApiError.badRequestError('Kill templates can not be assigned to desks')
        if 'is_public' in doc and doc['is_public'] is False:
            raise SuperdeskApiError.badRequestError(_('Kill templates must be public'))
        doc['is_public'] = True

    def _validate_template_desks(self, updates, original=None):
        """
        Validate template desks value
        """
        if original is None:
            original = {}
        template_type = updates.get('template_type', original.get('template_type'))
        if template_type != TemplateType.CREATE.value and \
                type(updates.get('template_desks')) == list and \
                len(updates['template_desks']) > 1:
            raise SuperdeskApiError.badRequestError(
                message=_('Templates that are not create type can only be assigned to one desk!'))

    def _process_kill_template(self, doc):
        """
        Marks certain field required by the kill as null.
        """
        if doc.get('template_type') != TemplateType.KILL.value:
            return

        for key in KILL_TEMPLATE_NOT_REQUIRED_FIELDS:
            if key in metadata_schema:
                doc.setdefault('data', {})
                doc['data'][key] = None
            else:
                doc[key] = None


class ContentTemplatesApplyResource(Resource):
    endpoint_name = 'content_templates_apply'
    resource_title = endpoint_name
    schema = {
        'template_name': {
            'type': 'string',
            'required': True
        },
        'item': {
            'type': 'dict',
            'required': True,
            'schema': item_schema()
        }
    }

    resource_methods = ['POST']
    item_methods = []
    privileges = {'POST': ARCHIVE}
    url = 'content_templates_apply'


class ContentTemplatesApplyService(Service):

    def create(self, docs, **kwargs):
        doc = docs[0] if len(docs) > 0 else {}
        template_name = doc.get('template_name')
        item = doc.get('item') or {}
        item['desk_name'] = get_resource_service('desks').get_desk_name(item.get('task', {}).get('desk'))

        if not template_name:
            SuperdeskApiError.badRequestError(message='Invalid Template Name')

        if not item:
            SuperdeskApiError.badRequestError(message='Invalid Item')

        template = superdesk.get_resource_service('content_templates').get_template_by_name(template_name)
        if not template:
            SuperdeskApiError.badRequestError(message='Invalid Template')

        updates = render_content_template(item, template)
        item.update(updates)

        if template_name == 'kill':
            apply_null_override_for_kill(item)

        docs[0] = item
        build_custom_hateoas(CUSTOM_HATEOAS, docs[0])
        return [docs[0].get(config.ID_FIELD)]


def render_content_template_by_name(item, template_name):
    """Apply template by name.

    :param dict item: item on which template is applied
    :param str template_name: template name
    :return dict: updates to the item
    """
    # get the kill template
    template = superdesk.get_resource_service('content_templates').get_template_by_name(template_name)
    if not template:
        SuperdeskApiError.badRequestError(message='{} Template missing.'.format(template_name))

    # apply the kill template
    return render_content_template(item, template)


def render_content_template_by_id(item, template_id):
    """Apply template by name.

    :param dict item: item on which template is applied
    :param str template_id: template _id
    :return dict: updates to the item
    """
    # get the kill template
    template = superdesk.get_resource_service('content_templates').find_one(req=None, _id=template_id)
    if not template:
        SuperdeskApiError.badRequestError(message='{} Template missing.'.format(template_id))

    return render_content_template(item, template)


def render_content_template(item, template):
    """Render the template.

    :param dict item: item on which template is applied
    :param dict template: template
    :return dict: updates to the item
    """
    updates = {}
    template_data = template.get('data', {})
    for key, value in template_data.items():
        if key in TEMPLATE_FIELDS or template_data.get(key) is None:
            continue

        if isinstance(value, str):
            updates[key] = render_template_string(value, item=item)
        elif (isinstance(value, dict) or isinstance(value, list)) and value:
            updates[key] = value
        elif not (isinstance(value, dict) or isinstance(value, list)):
            updates[key] = value

    filter_plaintext_fields(updates)

    return updates


def get_scheduled_templates(now):
    """Get templates that should be used to create items for given time.

    :param datetime now
    :return Cursor
    """
    return superdesk.get_resource_service('content_templates').get_scheduled_templates(now)


def set_template_timestamps(template, now):
    """Update template `next_run` field to next time it should run.

    :param dict template
    :param datetime now
    """
    updates = {
        'last_run': now,
        'next_run': get_next_run(template.get('schedule'), now),
    }
    service = superdesk.get_resource_service('content_templates')
    service.update(template[config.ID_FIELD], updates, template)


def get_item_from_template(template):
    """Get item dict using data from template.

    :param dict template
    """
    item = template.get('data', {})
    item[ITEM_STATE] = CONTENT_STATE.SUBMITTED
    if template.get('schedule_desk'):
        item['task'] = {'desk': template['schedule_desk'], 'stage': template.get('schedule_stage')}
    item['template'] = template.get('_id')
    item.pop('firstcreated', None)
    item.pop('versioncreated', None)

    # handle dateline
    dateline = item.get('dateline', {})
    dateline['date'] = utcnow()
    if dateline.get('located'):
        dateline['text'] = format_dateline_to_locmmmddsrc(dateline['located'], dateline['date'])

    filter_plaintext_fields(item)

    return item


def filter_plaintext_fields(item):
    """Filter out html from plaintext fields."""
    for field in PLAINTEXT_FIELDS:
        if field in item:
            item[field] = plaintext_filter(item[field])


def apply_null_override_for_kill(item):
    for key in app.config['KILL_TEMPLATE_NULL_FIELDS']:
        if key in item:
            item[key] = None


@celery.task(soft_time_limit=120)
def create_scheduled_content(now=None):
    lock_name = get_lock_id("Template", "Schedule")
    if not lock(lock_name, expire=130):
        logger.info('Task: {} is already running.'.format(lock_name))
        return

    try:
        if now is None:
            now = utcnow()
        templates = get_scheduled_templates(now)
        production = superdesk.get_resource_service(ARCHIVE)
        items = []
        for template in templates:
            set_template_timestamps(template, now)
            item = get_item_from_template(template)
            item[config.VERSION] = 1
            production.post([item])
            insert_into_versions(doc=item)
            try:
                apply_onstage_rule(item, item.get(config.ID_FIELD))
            except Exception as ex:  # noqa
                logger.exception('Failed to apply on stage rule while scheduling template.')
            items.append(item)
        return items
    except Exception as e:
        logger.exception('Task: {} failed with error {}.'.format(lock_name, str(e)))
    finally:
        unlock(lock_name)


def create_template_for_profile(items):
    """Create templates based on given profiles.

    Each template should have same name like profile.

    :param items: list of profiles
    """
    templates = []
    for profile in items:
        if profile.get('label'):
            templates.append({
                'template_name': profile.get('label'),
                'is_public': True,
                'data': {'profile': str(profile.get(config.ID_FIELD))}
            })
    if templates:
        superdesk.get_resource_service(CONTENT_TEMPLATE_RESOURCE).post(templates)


def remove_profile_from_templates(item):
    """Removes the profile data from templates that are using the profile

    :param item: deleted content profile
    """
    templates = list(superdesk.get_resource_service(CONTENT_TEMPLATE_RESOURCE).
                     get_templates_by_profile_id(item.get(config.ID_FIELD)))
    for template in templates:
        template.get('data', {}).pop('profile', None)
        superdesk.get_resource_service(CONTENT_TEMPLATE_RESOURCE).patch(template[config.ID_FIELD], template)
