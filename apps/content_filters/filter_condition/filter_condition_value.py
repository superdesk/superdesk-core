# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license
import re
from apps.content_filters.filter_condition.filter_condition_operator import FilterConditionOperatorsEnum


class FilterConditionValue:

    mongo_mapper = {FilterConditionOperatorsEnum.startswith: '^{}',
                    FilterConditionOperatorsEnum.like: '.*{}.*',
                    FilterConditionOperatorsEnum.notlike: '.*{}.*',
                    FilterConditionOperatorsEnum.endswith: '.*{}'}

    elastic_mapper = {FilterConditionOperatorsEnum.startswith: '{}:{}*',
                      FilterConditionOperatorsEnum.like: '{}:*{}*',
                      FilterConditionOperatorsEnum.notlike: '{}:*{}*',
                      FilterConditionOperatorsEnum.endswith: '{}:*{}'}

    def __init__(self, operator, value):
        self.operator = operator
        self.value = value
        self.mongo_regex = self.mongo_mapper.get(operator.operator)
        self.elastic_regex = self.elastic_mapper.get(operator.operator)

    def get_mongo_value(self, field):
        if self.mongo_regex:
            return self._get_regex_value()
        else:
            return self._get_value(field)

    def get_elastic_value(self, field):
        if self.elastic_regex:
            return self.elastic_regex.format(field.get_entity_name(), self.value), 'query'
        else:
            return self._get_value(field), field.get_entity_name()

    def _get_regex_value(self):
        return re.compile(self.mongo_regex.format(self.value), re.IGNORECASE)

    def _get_value(self, field):
        t = field.get_type()
        if self.value.find(',') > 0:
            return [t(x) for x in self.value.strip().split(',')]
        return [t(self.value)]
