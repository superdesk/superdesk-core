# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license
from apps.content_filters.filter_condition.filter_condition_field import FilterConditionField
from apps.content_filters.filter_condition.filter_condition_value import FilterConditionValue
from apps.content_filters.filter_condition.filter_condition_operator import \
    FilterConditionOperator, NotInOperator, NotLikeOperator


class FilterCondition:

    def __init__(self, field, operator, value):
        self.field = FilterConditionField.factory(field)
        self.operator = FilterConditionOperator.factory(operator)
        self.value = FilterConditionValue(self.operator, value)

    @staticmethod
    def parse(filter_condition):
        return FilterCondition(filter_condition['field'],
                               filter_condition['operator'],
                               filter_condition['value'])

    def get_mongo_query(self):
        field = self.field.get_entity_name()
        operator = self.operator.get_mongo_operator()
        value = self.value.get_mongo_value(self.field)
        return {field: {operator: value}}

    def get_elastic_query(self):
        field = self.field.get_entity_name()
        operator = self.operator.get_elastic_operator()
        value, field = self.value.get_elastic_value(self.field)
        return {operator: {field: value}}

    def does_match(self, article):

        if not self.field.is_in_article(article):
            return type(self.operator) is NotInOperator or type(self.operator) is NotLikeOperator

        article_value = self.field.get_value(article)
        filter_value = self.value.get_mongo_value(self.field)
        return self.operator.does_match(article_value, filter_value)
