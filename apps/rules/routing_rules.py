# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import logging
import superdesk

import pytz
from pytz import all_timezones_set

from enum import Enum
from datetime import datetime, timedelta
from superdesk import get_resource_service
from superdesk.resource import Resource
from superdesk.services import BaseService
from superdesk.errors import SuperdeskApiError
from eve.utils import config
from superdesk.metadata.item import CONTENT_STATE
from superdesk.utc import set_time
from flask_babel import _

logger = logging.getLogger(__name__)


class Weekdays(Enum):
    """Weekdays names we use for scheduling."""

    MON = 0
    TUE = 1
    WED = 2
    THU = 3
    FRI = 4
    SAT = 5
    SUN = 6

    @classmethod
    def is_valid_schedule(cls, list_of_days):
        """Test if all days in list_of_days are valid day names.

        :param list list_of_days eg. ['mon', 'tue', 'fri']
        """
        return all([day.upper() in cls.__members__ for day in list_of_days])

    @classmethod
    def is_scheduled_day(cls, today, list_of_days):
        """Test if today's weekday is in schedule.

        :param datetime today
        :param list list_of_days
        """
        return today.weekday() in [cls[day.upper()].value for day in list_of_days]

    @classmethod
    def dayname(cls, day):
        """Get name shortcut (MON, TUE, ...) for given day.

        :param datetime day
        """
        return cls(day.weekday()).name


class RoutingRuleSchemeResource(Resource):
    """
    Resource class for 'routing_schemes' endpoint
    """

    schema = {
        'name': {
            'type': 'string',
            'iunique': True,
            'required': True,
            'nullable': False,
            'empty': False
        },
        'rules': {
            'type': 'list',
            'schema': {
                'type': 'dict',
                'schema': {
                    'name': {
                        'type': 'string'
                    },
                    'filter': Resource.rel('content_filters', nullable=True),
                    'actions': {
                        'type': 'dict',
                        'schema': {
                            'fetch': {
                                'type': 'list',
                                'schema': {
                                    'type': 'dict',
                                    'schema': {
                                        'desk': Resource.rel('desks', True),
                                        'stage': Resource.rel('stages', True),
                                        'macro': {'type': 'string'}
                                    }
                                }
                            },
                            'publish': {
                                'type': 'list',
                                'schema': {
                                    'type': 'dict',
                                    'schema': {
                                        'desk': Resource.rel('desks', True),
                                        'stage': Resource.rel('stages', True),
                                        'macro': {'type': 'string'},
                                        'target_subscribers': {
                                            'type': 'list',
                                            'nullable': True
                                        },
                                        'target_types': {
                                            'type': 'list',
                                            'nullable': True
                                        }
                                    }
                                }
                            },
                            'exit': {
                                'type': 'boolean'
                            },
                            'preserve_desk': {
                                'type': 'boolean'
                            }
                        }
                    },
                    'schedule': {
                        'type': 'dict',
                        'nullable': True,
                        'schema': {
                            'day_of_week': {
                                'type': 'list'
                            },
                            'hour_of_day_from': {
                                'type': 'string',
                                'nullable': True,
                            },
                            'hour_of_day_to': {
                                'type': 'string',
                                'nullable': True,
                            },
                            'time_zone': {
                                'type': 'string',
                                'nullable': False,
                                'default': 'UTC'
                            }
                        }
                    }
                }
            }
        }
    }

    privileges = {'POST': 'routing_rules', 'DELETE': 'routing_rules', 'PATCH': 'routing_rules'}


class RoutingRuleSchemeService(BaseService):
    """
    Service class for 'routing_schemes' endpoint.
    """

    def on_create(self, docs):
        """Overriding to check the below pre-conditions:

            1. A routing scheme must have at least one rule.
            2. Every rule in the routing scheme must have name, filter and at least one action

        Will throw BadRequestError if any of the pre-conditions fail.
        """
        for routing_scheme in docs:
            self._adjust_for_empty_schedules(routing_scheme)
            self._validate_routing_scheme(routing_scheme)
            self._check_if_rule_name_is_unique(routing_scheme)

    def on_update(self, updates, original):
        """Overriding to check the below pre-conditions:

            1. A routing scheme must have at least one rule.
            2. Every rule in the routing scheme must have name, filter and at least one action

        Will throw BadRequestError if any of the pre-conditions fail.
        """
        self._adjust_for_empty_schedules(updates)
        self._validate_routing_scheme(updates)
        self._check_if_rule_name_is_unique(updates)

    def on_delete(self, doc):
        """Overriding to check the below pre-conditions:

            1. A routing scheme shouldn't be associated with an Ingest Provider.

        Will throw BadRequestError if any of the pre-conditions fail.
        """

        if self.backend.find_one('ingest_providers', req=None, routing_scheme=doc[config.ID_FIELD]):
            raise SuperdeskApiError.forbiddenError(
                _('Routing scheme is applied to channel(s). It cannot be deleted.'))

    def apply_routing_scheme(self, ingest_item, provider, routing_scheme):
        """Applies routing scheme and applies appropriate action (fetch, publish) to the item

        :param item: ingest item to which routing scheme needs to applied.
        :param provider: provider for which the routing scheme is applied.
        :param routing_scheme: routing scheme.
        """
        rules = routing_scheme.get('rules', [])
        if not rules:
            logger.warning("Routing Scheme % for provider % has no rules configured." %
                           (provider.get('name'), routing_scheme.get('name')))

        filters_service = superdesk.get_resource_service('content_filters')

        now = datetime.utcnow()

        for rule in self._get_scheduled_routing_rules(rules, now):
            content_filter = rule.get('filter', {})
            logger.info('Applying rule. Item: %s . Routing Scheme: %s. Rule Name %s.' % (ingest_item.get('guid'),
                                                                                         routing_scheme.get('name'),
                                                                                         rule.get('name')))
            if filters_service.does_match(content_filter, ingest_item):
                logger.info('Filter matched. Item: %s. Routing Scheme: %s. Rule Name %s.' % (ingest_item.get('guid'),
                                                                                             routing_scheme.get('name'),
                                                                                             rule.get('name')))
                if rule.get('actions', {}).get('preserve_desk', False) and ingest_item.get('task', {}).get('desk'):
                    desk = get_resource_service('desks').find_one(req=None, _id=ingest_item['task']['desk'])
                    if ingest_item.get('task', {}).get('stage'):
                        stage_id = ingest_item['task']['stage']
                    else:
                        stage_id = desk['incoming_stage']
                    self.__fetch(ingest_item, [{'desk': desk[config.ID_FIELD], 'stage': stage_id}])
                    fetch_actions = [f for f in rule.get('actions', {}).get('fetch', [])
                                     if f.get('desk') != ingest_item['task']['desk']]
                else:
                    fetch_actions = rule.get('actions', {}).get('fetch', [])

                self.__fetch(ingest_item, fetch_actions)
                self.__publish(ingest_item, rule.get('actions', {}).get('publish', []))
                if rule.get('actions', {}).get('exit', False):
                    logger.info('Exiting routing scheme. Item: %s . Routing Scheme: %s. '
                                'Rule Name %s.' % (ingest_item.get('guid'), routing_scheme.get('name'),
                                                   rule.get('name')))
                    break
            else:
                logger.info("Routing rule %s of Routing Scheme %s for Provider %s did not match for item %s" %
                            (rule.get('name'), routing_scheme.get('name'),
                             provider.get('name'), ingest_item[config.ID_FIELD]))

    def _adjust_for_empty_schedules(self, routing_scheme):
        """Adjust for empty schedules.

        For all routing scheme's rules, set their non-empty schedules to
        None if they are effectively not defined.

        A schedule is recognized as "not defined" if it only contains time zone
        information without anything else. This can happen if an empty schedule
        is submitted by the client, because `Eve` then converts it to the
        following:

            {'time_zone': 'UTC'}

        This is because the time_zone field has a default value set in the
        schema, and Eve wants to apply it even when the containing object (i.e.
        the schedule) is None and there is nothing that would contain the time
        zone information.

        :param dict routing_scheme: the routing scheme to check
        """
        for rule in routing_scheme.get('rules', []):
            schedule = rule.get('schedule')
            if schedule:
                if set(schedule.keys()) == {'time_zone'}:
                    rule['schedule'] = None
                elif 'time_zone' not in schedule.keys():
                    schedule['time_zone'] = 'UTC'

    def _validate_routing_scheme(self, routing_scheme):
        """Validates routing scheme for the below:

            1. A routing scheme must have at least one rule.
            2. Every rule in the routing scheme must have name, filter and at least one action

        Will throw BadRequestError if any of the conditions fail.

        :param routing_scheme:
        """

        routing_rules = routing_scheme.get('rules', [])
        if len(routing_rules) == 0:
            raise SuperdeskApiError.badRequestError(message=_("A Routing Scheme must have at least one Rule"))
        for routing_rule in routing_rules:
            invalid_fields = [field for field in routing_rule.keys()
                              if field not in ('name', 'filter', 'actions', 'schedule')]

            if invalid_fields:
                raise SuperdeskApiError.badRequestError(
                    message=_("A routing rule has invalid fields {fields}").format(fields=invalid_fields))

            schedule = routing_rule.get('schedule')
            actions = routing_rule.get('actions')

            if routing_rule.get('name') is None:
                raise SuperdeskApiError.badRequestError(message=_("A routing rule must have a name"))
            elif actions is None or len(actions) == 0 or (actions.get('fetch') is None and actions.get(
                    'publish') is None and actions.get('exit') is None):
                raise SuperdeskApiError.badRequestError(message=_("A routing rule must have actions"))
            else:
                self._validate_schedule(schedule)

    def _validate_schedule(self, schedule):
        """Validate schedule.

        Check if the given routing schedule configuration is valid and raise
        an error if this is not the case.

        :param dict schedule: the routing schedule configuration to validate

        :raises SuperdeskApiError: if validation of `schedule` fails
        """
        if schedule is not None and (
            len(schedule) == 0 or
            schedule.get('day_of_week') is None or
            len(schedule.get('day_of_week', [])) == 0
        ):
            raise SuperdeskApiError.badRequestError(message=_("Schedule when defined can't be empty."))

        if schedule:
            if not Weekdays.is_valid_schedule(schedule.get('day_of_week', [])):
                raise SuperdeskApiError.badRequestError(message=_("Invalid values for day of week."))

            if schedule.get('hour_of_day_from') or schedule.get('hour_of_day_to'):
                try:
                    from_time = datetime.strptime(schedule.get('hour_of_day_from'), '%H:%M:%S')
                except Exception:
                    raise SuperdeskApiError.badRequestError(message=_("Invalid value for from time."))

                to_time = schedule.get('hour_of_day_to', '')
                if to_time:
                    try:
                        to_time = datetime.strptime(to_time, '%H:%M:%S')
                    except Exception:
                        raise SuperdeskApiError.badRequestError(
                            message=_("Invalid value for hour_of_day_to (expected %H:%M:%S)."))

                    if from_time > to_time:
                        raise SuperdeskApiError.badRequestError(
                            message=_("From time should be less than To Time.")
                        )

            time_zone = schedule.get('time_zone')

            if time_zone and (time_zone not in all_timezones_set):
                msg = _('Unknown time zone {time_zone}').format(time_zone=time_zone)
                raise SuperdeskApiError.badRequestError(message=msg)

    def _check_if_rule_name_is_unique(self, routing_scheme):
        """
        Checks if name of a routing rule is unique or not.
        """
        routing_rules = routing_scheme.get('rules', [])

        for routing_rule in routing_rules:
            rules_with_same_name = [rule for rule in routing_rules if rule.get('name') == routing_rule.get('name')]

            if len(rules_with_same_name) > 1:
                raise SuperdeskApiError.badRequestError(_("Rule Names must be unique within a scheme"))

    def _get_scheduled_routing_rules(self, rules, current_dt_utc):
        """
        Iterates rules list and returns the list of rules that are scheduled.

        :param list rules: routing rules to check
        :param datetime current_dt_utc: the value to take as the current
            time in UTC

        :return: the rules scheduled to be appplied at `current_dt_utc`
        :rtype: list
        """
        # make it a timezone-aware object
        current_dt_utc = current_dt_utc.replace(tzinfo=pytz.utc)
        delta_minute = timedelta(minutes=1)

        scheduled_rules = []
        for rule in rules:
            is_scheduled = True
            schedule = rule.get('schedule', {})
            if schedule:
                # adjust current time to the schedule's timezone
                tz_name = schedule.get('time_zone')
                schedule_tz = pytz.timezone(tz_name) if tz_name else pytz.utc
                now_tz_schedule = current_dt_utc.astimezone(tz=schedule_tz)

                # Create start and end time-of-day limits. If start time is not
                # defined, the beginning of the day is assumed. If end time
                # is not defined, the end of the day is assumed (excluding the
                # midnight, since at that point a new day has already begun).
                hour_of_day_from = schedule.get('hour_of_day_from')
                if not hour_of_day_from:
                    hour_of_day_from = '00:00:00'  # might be both '' or None
                from_time = set_time(now_tz_schedule, hour_of_day_from)

                hour_of_day_to = schedule.get('hour_of_day_to')
                if hour_of_day_to:
                    to_time = set_time(now_tz_schedule, hour_of_day_to)
                    if hour_of_day_to[-2:] == '00':
                        to_time = to_time + delta_minute
                else:
                    to_time = set_time(now_tz_schedule, '23:59:59') + delta_minute

                # check if the current day of week and time of day both match
                day_of_week_matches = Weekdays.is_scheduled_day(
                    now_tz_schedule, schedule.get('day_of_week', []))
                time_of_day_matches = (from_time <= now_tz_schedule < to_time)

                is_scheduled = (day_of_week_matches and time_of_day_matches)

            if is_scheduled:
                scheduled_rules.append(rule)

        return scheduled_rules

    def __fetch(self, ingest_item, destinations):
        """Fetch to item to the destinations

        :param item: item to be fetched
        :param destinations: list of desk and stage
        """
        archive_items = []
        for destination in destinations:
            try:
                logger.info('Fetching item %s to desk %s' % (ingest_item.get('guid'), destination))
                target = self.__getTarget(destination)
                item_id = get_resource_service('fetch') \
                    .fetch([{config.ID_FIELD: ingest_item[config.ID_FIELD],
                             'desk': str(destination.get('desk')),
                             'stage': str(destination.get('stage')),
                             'state': CONTENT_STATE.ROUTED,
                             'macro': destination.get('macro', None),
                             'target': target}])[0]

                archive_items.append(item_id)
                logger.info('Fetched item %s to desk %s' % (ingest_item.get('guid'), destination))
            except Exception:
                logger.exception("Failed to fetch item %s to desk %s" % (ingest_item.get('guid'), destination))

        return archive_items

    def __getTarget(self, destination):
        """Get the target for destination

        :param dict destination: routing destination
        :return dict: returns target information
        """
        target = {}
        if destination.get('target_subscribers'):
            target['target_subscribers'] = destination.get('target_subscribers')

        if destination.get('target_types'):
            target['target_types'] = destination.get('target_types')

        return target

    def __publish(self, ingest_item, destinations):
        """Fetches the item to the desk and then publishes the item.

        :param item: item to be published
        :param destinations: list of desk and stage
        """
        items_to_publish = self.__fetch(ingest_item, destinations)
        for item in items_to_publish:
            try:
                logger.info('Publishing item %s' % (ingest_item.get('guid')))
                self._set_default_values(item)
                get_resource_service('archive_publish').patch(item, {'auto_publish': True})
                logger.info('Published item %s' % (ingest_item.get('guid')))
            except Exception:
                logger.exception("Failed to publish item %s." % item)

    def _set_default_values(self, item):
        """Assigns the default values to the item that about to be auto published"""

        archive_item = get_resource_service('archive').find_one(req=None, _id=item)
        default_categories = self._get_categories(config.DEFAULT_CATEGORY_QCODES_FOR_AUTO_PUBLISHED_ARTICLES)
        default_values = self._assign_default_values(archive_item, default_categories)
        get_resource_service('archive').patch(item, default_values)

    def _assign_default_values(self, archive_item, default_categories):
        """Assigns the default values to the item that about to be auto published"""

        default_values = {}
        default_values['headline'] = archive_item.get('headline') or ' '

        if archive_item.get('anpa_category'):
            default_values['anpa_category'] = archive_item.get('anpa_category')
        else:
            default_values['anpa_category'] = default_categories

        default_values['slugline'] = archive_item.get('slugline') or ' '
        default_values['body_html'] = archive_item.get('body_html') or '<p></p>'
        return default_values

    def _get_categories(self, qcodes):
        """Returns list of categories for a given comma separated qcodes"""

        if not qcodes:
            return

        qcode_list = qcodes.split(',')
        selected_categories = None
        categories = superdesk.get_resource_service('vocabularies').find_one(req=None, _id='categories')

        if categories and len(qcode_list) > 0:
            selected_categories = []
            for qcode in qcode_list:
                selected_categories.extend([{'qcode': qcode, 'name': c.get('name', '')} for c in categories['items']
                                            if c['is_active'] is True and
                                            qcode.lower() == c['qcode'].lower()])

        return selected_categories
