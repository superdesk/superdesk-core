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
from superdesk import Resource, Service, config, get_resource_service
from superdesk.utils import SuperdeskBaseEnum
from superdesk.resource import build_custom_hateoas
from superdesk.utc import utcnow, set_time, local_to_utc
from superdesk.errors import SuperdeskApiError
from superdesk.metadata.item import metadata_schema, ITEM_STATE, CONTENT_STATE
from superdesk.celery_app import celery
from superdesk.utils import plaintext_filter
from apps.rules.routing_rules import Weekdays
from apps.archive.common import ARCHIVE, CUSTOM_HATEOAS, item_schema, format_dateline_to_locmmmddsrc
from apps.archive.common import insert_into_versions, ARCHIVE_SCHEMA_FIELDS
from apps.auth import get_user
from flask import render_template_string
from datetime import timedelta
from copy import deepcopy
import logging
from superdesk.lock import lock, unlock
from superdesk.celery_task_utils import get_lock_id


CONTENT_TEMPLATE_PRIVILEGE = 'content_templates'
TEMPLATE_FIELDS = {'template_name', 'template_type', 'schedule', 'type', 'state',
                   'last_run', 'next_run', 'template_desks', 'schedule_desk', 'schedule_stage',
                   config.ID_FIELD, config.LAST_UPDATED, config.DATE_CREATED,
                   config.ETAG, 'task'}
KILL_TEMPLATE_NOT_REQUIRED_FIELDS = ['schedule', 'dateline', 'template_desks', 'schedule_desk',
                                     'schedule_stage']
KILL_TEMPLATE_NULL_FIELDS = ['byline', 'place']
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


def get_next_run(schedule, now=None):
    """Get next run time based on schedule.

    Schedule is day of week and time.

    :param dict schedule: dict with `day_of_week` and `create_at` params
    :param datetime now
    :return datetime
    """
    if not schedule.get('is_active', False):
        return None

    allowed_days = [Weekdays[day.upper()].value for day in schedule.get('day_of_week', [])]
    if not allowed_days:
        return None

    if now is None:
        now = utcnow()

    now = now.replace(second=0)

    # adjust current time to the schedule's timezone
    tz_name = schedule.get('time_zone', 'UTC')
    if tz_name != 'UTC':
        next_run = local_to_utc(tz_name, set_time(now, schedule.get('create_at')))
    else:
        next_run = set_time(now, schedule.get('create_at'))

    # if the time passed already today do it tomorrow earliest
    if next_run <= now:
        next_run += timedelta(days=1)

    while next_run.weekday() not in allowed_days:
        next_run += timedelta(days=1)

    return next_run


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


class ContentTemplatesService(Service):

    def on_create(self, docs):
        for doc in docs:
            doc['template_name'] = doc['template_name'].lower().strip()
            if doc.get('schedule'):
                doc['next_run'] = get_next_run(doc.get('schedule'))

            if doc.get('template_type') == TemplateType.KILL.value and \
                    any(key for key in doc.keys() if key in KILL_TEMPLATE_NOT_REQUIRED_FIELDS):
                raise SuperdeskApiError.badRequestError(
                    message="Invalid kill template. "
                            "{} are not allowed".format(', '.join(KILL_TEMPLATE_NOT_REQUIRED_FIELDS)))
            if doc.get('template_type') == TemplateType.KILL.value:
                self._validate_kill_template(doc)
            if get_user():
                doc.setdefault('user', get_user()[config.ID_FIELD])
            self._validate_template_desks(doc)

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

    def on_delete(self, doc):
        if doc.get('template_type') == TemplateType.KILL.value:
            raise SuperdeskApiError.badRequestError('Kill templates can not be deleted.')

    def get_scheduled_templates(self, now):
        """Get the template by schedule

        :param datetime now:
        :return MongoCursor:
        """
        query = {'next_run': {'$lte': now}, 'schedule.is_active': True}
        return self.find(query)

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
            raise SuperdeskApiError.badRequestError('Kill templates must be public')
        doc['is_public'] = True

    def _validate_template_desks(self, updates, original={}):
        """
        Validate template desks value
        """
        template_type = updates.get('template_type', original.get('template_type'))
        if template_type != TemplateType.CREATE.value and \
                type(updates.get('template_desks')) == list and \
                len(updates['template_desks']) > 1:
            raise SuperdeskApiError.badRequestError(
                message='Templates that are not create type can only be assigned to one desk!')

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
    service.update(template['_id'], updates, template)


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
    for key in KILL_TEMPLATE_NULL_FIELDS:
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
            items.append(item)
        return items
    except Exception as e:
        logger.exception('Task: {} failed with error {}.'.format(lock_name, str(e)))
    finally:
        unlock(lock_name)
