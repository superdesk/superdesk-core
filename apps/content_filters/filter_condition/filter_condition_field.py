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
    body_html = 13


class FilterConditionField:

    field_mappings = {FilterConditionFieldsEnum.anpa_category: 'anpa_category.qcode',
                      FilterConditionFieldsEnum.genre: 'genre.name',
                      FilterConditionFieldsEnum.subject: 'subject.qcode',
                      FilterConditionFieldsEnum.desk: 'task.desk',
                      FilterConditionFieldsEnum.sms: 'flags.marked_for_sms'}

    field_type_mappings = {FilterConditionFieldsEnum.urgency: int,
                           FilterConditionFieldsEnum.sms: bool}

    def __init__(self, field):
        self.field = FilterConditionFieldsEnum[field]
        self.entity_name = self.field_mappings.get(self.field, field)
        self.field_type = self.field_type_mappings.get(self.field, str)

    def get_entity_name(self):
        return self.entity_name

    def get_type(self):
        return self.field_type

    def is_in_article(self, article):
        if self.field == FilterConditionFieldsEnum.desk:
            return self.field in article.get('task', {})
        elif self.field == FilterConditionFieldsEnum.sms:
            return 'marked_for_sms' in article.get('flags', {})
        else:
            return self.field._name_ in article

    def get_value(self, article):
        if self.field == FilterConditionFieldsEnum.anpa_category:
            return [c['qcode'] for c in article[self.field._name_]]
        elif self.field == FilterConditionFieldsEnum.genre:
            return [g['name'] for g in article[self.field._name_]]
        elif self.field == FilterConditionFieldsEnum.subject:
            return [s['qcode'] for s in article[self.field._name_]]
        elif self.field == FilterConditionFieldsEnum.desk:
            return str(article.get('task', {}).get(self.field._name_))
        elif self.field == FilterConditionFieldsEnum.sms:
            return str(article.get('flags', {}).get('marked_for_sms'))
        else:
            return article[self.field._name_]
