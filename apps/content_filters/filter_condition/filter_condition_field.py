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
from bs4 import BeautifulSoup


class FilterConditionFieldsEnum(Enum):
    anpa_category = 1,
    genre = 2,
    subject = 3,
    desk = 4,
    sms = 5,
    urgency = 6,
    priority = 7,
    type = 8,
    keywords = 9,
    slugline = 10,
    source = 11,
    headline = 12,
    body_html = 13,
    stage = 14,
    ednote = 15


class FilterConditionField:

    @staticmethod
    def factory(field):
        if FilterConditionFieldsEnum[field] == FilterConditionFieldsEnum.desk:
            return FilterConditionDeskField(field)
        elif FilterConditionFieldsEnum[field] == FilterConditionFieldsEnum.stage:
            return FilterConditionStageField(field)
        elif FilterConditionFieldsEnum[field] == FilterConditionFieldsEnum.anpa_category:
            return FilterConditionCategoryField(field)
        elif FilterConditionFieldsEnum[field] == FilterConditionFieldsEnum.genre:
            return FilterConditionGenreField(field)
        elif FilterConditionFieldsEnum[field] == FilterConditionFieldsEnum.sms:
            return FilterConditionSmsField(field)
        elif FilterConditionFieldsEnum[field] == FilterConditionFieldsEnum.subject:
            return FilterConditionSubjectField(field)
        elif FilterConditionFieldsEnum[field] == FilterConditionFieldsEnum.urgency:
            return FilterConditionUrgencyField(field)
        else:
            return FilterConditionField(field)

    def __init__(self, field):
        self.field = FilterConditionFieldsEnum[field]
        self.entity_name = field
        self.field_type = str

    def get_entity_name(self):
        return self.entity_name

    def get_type(self):
        return self.field_type

    def is_in_article(self, article):
        return self.field.name in article and article.get(self.field.name) is not None

    def get_value(self, article):
        try:
            soup = BeautifulSoup(article[self.field.name], "html.parser")
            return soup.get_text().replace('\n', ' ')
        except:
            return article[self.field.name]


class FilterConditionDeskField(FilterConditionField):
    def __init__(self, field):
        self.field = FilterConditionFieldsEnum.desk
        self.entity_name = 'task.desk'
        self.field_type = str

    def is_in_article(self, article):
        return self.field.name in article.get('task', {})

    def get_value(self, article):
        return str(article.get('task', {}).get(self.field.name))


class FilterConditionStageField(FilterConditionField):
    def __init__(self, field):
        self.field = FilterConditionFieldsEnum.stage
        self.entity_name = 'task.stage'
        self.field_type = str

    def is_in_article(self, article):
        return self.field.name in article.get('task', {})

    def get_value(self, article):
        return str(article.get('task', {}).get(self.field.name))


class FilterConditionSubjectField(FilterConditionField):
    def __init__(self, field):
        self.field = FilterConditionFieldsEnum.subject
        self.entity_name = 'subject.qcode'
        self.field_type = str

    def get_value(self, article):
        return [s['qcode'] for s in article[self.field.name]]


class FilterConditionCategoryField(FilterConditionField):
    def __init__(self, field):
        self.field = FilterConditionFieldsEnum.anpa_category
        self.entity_name = 'anpa_category.qcode'
        self.field_type = str

    def get_value(self, article):
        return [c['qcode'] for c in article[self.field.name]]


class FilterConditionGenreField(FilterConditionField):
    def __init__(self, field):
        self.field = FilterConditionFieldsEnum.genre
        self.entity_name = 'genre.name'
        self.field_type = str

    def get_value(self, article):
        return [g['name'] for g in article[self.field.name]]


class FilterConditionUrgencyField(FilterConditionField):
    def __init__(self, field):
        self.field = FilterConditionFieldsEnum[field]
        self.entity_name = field
        self.field_type = int


class FilterConditionSmsField(FilterConditionField):
    def __init__(self, field):
        self.field = FilterConditionFieldsEnum.sms
        self.entity_name = 'flags.marked_for_sms'
        self.field_type = bool

    def is_in_article(self, article):
        return 'marked_for_sms' in article.get('flags', {})

    def get_value(self, article):
        return str(article.get('flags', {}).get('marked_for_sms'))
