# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from enum import Enum
import operator


class FilterConditionOperatorsEnum(Enum):
    in_ = 1,
    nin = 2,
    like = 3,
    notlike = 4,
    startswith = 5,
    endswith = 6,
    match = 7,
    eq = 8,
    ne = 9,
    gt = 10,
    gte = 11,
    lt = 12,
    lte = 13


class FilterConditionOperator:

    @staticmethod
    def factory(operator):
        if operator + '_' == FilterConditionOperatorsEnum.in_.name:
            return InOperator(operator)
        elif operator == FilterConditionOperatorsEnum.nin.name:
            return NotInOperator(operator)
        elif operator == FilterConditionOperatorsEnum.notlike.name:
            return NotLikeOperator(operator)
        elif operator == FilterConditionOperatorsEnum.match.name:
            return MatchOperator(operator)
        elif operator in [FilterConditionOperatorsEnum.eq.name,
                          FilterConditionOperatorsEnum.ne.name,
                          FilterConditionOperatorsEnum.gt.name,
                          FilterConditionOperatorsEnum.gte.name,
                          FilterConditionOperatorsEnum.lt.name,
                          FilterConditionOperatorsEnum.lte.name]:
            return ComparisonOperator(operator)
        else:
            return RegexOperator(operator)

    def _get_default_mongo_operator(self):
        return '${}'.format(self.operator.name)

    def get_mongo_operator(self):
        return self.mongo_operator

    def get_elastic_operator(self):
        return self.elastic_operator

    def contains_not(self):
        return False

    def does_match(self, article_value, filter_value):
        raise NotImplementedError()

    def get_lower_case(self, value):
            return str(value).lower()


class InOperator(FilterConditionOperator):
    def __init__(self, operator):
        self.operator = FilterConditionOperatorsEnum[operator + '_']
        self.mongo_operator = '$in'
        self.elastic_operator = 'terms'

    def does_match(self, article_value, filter_value):
        if isinstance(article_value, list):
            return any([self.get_lower_case(v) in map(self.get_lower_case, filter_value) for v in article_value])
        else:
            return self.get_lower_case(article_value) in map(self.get_lower_case, filter_value)


class NotInOperator(FilterConditionOperator):
    def __init__(self, operator):
        self.operator = FilterConditionOperatorsEnum[operator]
        self.mongo_operator = self._get_default_mongo_operator()
        self.elastic_operator = 'terms'

    def does_match(self, article_value, filter_value):
        if isinstance(article_value, list):
            return all([self.get_lower_case(v) not in map(self.get_lower_case, filter_value) for v in article_value])
        else:
            return self.get_lower_case(article_value) not in map(self.get_lower_case, filter_value)

    def contains_not(self):
        return True


class NotLikeOperator(FilterConditionOperator):
    def __init__(self, operator):
        self.operator = FilterConditionOperatorsEnum[operator]
        self.mongo_operator = '$not'
        self.elastic_operator = 'query_string'

    def does_match(self, article_value, filter_value):
        return filter_value.match(article_value) is None

    def contains_not(self):
        return True


class ComparisonOperator(FilterConditionOperator):
    """
    Represents comparison operators
    """

    _operators = {FilterConditionOperatorsEnum.gt: operator.gt,
                  FilterConditionOperatorsEnum.lt: operator.lt,
                  FilterConditionOperatorsEnum.gte: operator.ge,
                  FilterConditionOperatorsEnum.lte: operator.le,
                  FilterConditionOperatorsEnum.ne: operator.ne,
                  FilterConditionOperatorsEnum.eq: operator.eq}

    _elastic_mapper = {FilterConditionOperatorsEnum.gt: '{{"range": {{"{}": {{"gt": "{}"}}}}}}',
                       FilterConditionOperatorsEnum.gte: '{{"range": {{"{}": {{"gte": "{}"}}}}}}',
                       FilterConditionOperatorsEnum.lt: '{{"range": {{"{}": {{"lt": "{}"}}}}}}',
                       FilterConditionOperatorsEnum.lte: '{{"range": {{"{}": {{"lte": "{}"}}}}}}',
                       FilterConditionOperatorsEnum.eq: '{{"term": {{"{}": "{}"}}}}',
                       FilterConditionOperatorsEnum.ne: '{{"term": {{"{}": "{}"}}}}'}

    def __init__(self, operator):
        self.operator = FilterConditionOperatorsEnum[operator]
        self.operator_func = ComparisonOperator._operators[FilterConditionOperatorsEnum[operator]]
        self.mongo_operator = self._get_default_mongo_operator()
        self.elastic_operator = ComparisonOperator._elastic_mapper[FilterConditionOperatorsEnum[operator]]

    def contains_not(self):
        return self.operator == FilterConditionOperatorsEnum.ne

    def does_match(self, article_value, filter_value):
        try:
            if isinstance(filter_value, bool):
                article_value = article_value.lower() in ("yes", "true", "t", "1")
            else:
                t = type(filter_value)
                article_value = t(article_value)

            if isinstance(filter_value, str):
                article_value = self.get_lower_case(article_value).strip()
                filter_value = self.get_lower_case(filter_value).strip()
            return self.operator_func(article_value, filter_value)
        except:
            return False


class RegexOperator(FilterConditionOperator):
    """
    Represents In, StartsWith and EndsWith operators
    """

    def __init__(self, operator):
        self.operator = FilterConditionOperatorsEnum[operator]
        self.mongo_operator = '$regex'
        self.elastic_operator = 'query_string'

    def does_match(self, article_value, filter_value):
        return filter_value.match(article_value) is not None


class MatchOperator(FilterConditionOperator):
    def __init__(self, operator):
        self.operator = FilterConditionOperatorsEnum[operator]
        self.mongo_operator = '$in'
        self.elastic_operator = '{{"query_string": {{"{}":"{}"}}}}'

    def does_match(self, article_value, filter_value):
        if isinstance(article_value, list):
            return any([self.get_lower_case(v) in map(self.get_lower_case, filter_value) for v in article_value])
        else:
            return self.get_lower_case(article_value) in map(self.get_lower_case, filter_value)
