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
from lxml import etree
from superdesk.text_utils import get_text
from superdesk.utc import utcnow
from superdesk import get_resource_service
from superdesk.errors import SuperdeskApiError
from flask_babel import _


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
    ednote = 15,
    place = 16,
    ingest_provider = 17
    embargo = 18
    featuremedia = 19
    agendas = 20


class FilterConditionField:

    @staticmethod
    def factory(field):
        if field not in FilterConditionFieldsEnum.__members__:
            vocabulary = get_resource_service('vocabularies').find_one(req=None, _id=field)
            if vocabulary:
                if vocabulary.get('field_type', '') == 'text':
                    return FilterConditionCustomTextField(field)
                else:
                    return FilterConditionControlledVocabularyField(field)
            raise SuperdeskApiError.internalError(_('Invalid filter conditions field {field}').format(field=field))
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
        elif FilterConditionFieldsEnum[field] == FilterConditionFieldsEnum.priority:
            return FilterConditionPriorityField(field)
        elif FilterConditionFieldsEnum[field] == FilterConditionFieldsEnum.place:
            return FilterConditionPlaceField(field)
        elif FilterConditionFieldsEnum[field] == FilterConditionFieldsEnum.ingest_provider:
            return FilterConditionIngestProviderField(field)
        elif FilterConditionFieldsEnum[field] == FilterConditionFieldsEnum.embargo:
            return FilterConditionEmbargoField(field)
        elif FilterConditionFieldsEnum[field] == FilterConditionFieldsEnum.featuremedia:
            return FilterConditionFeatureMediaField(field)
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
            return get_text(article[self.field.name]).strip()
        except (etree.XMLSyntaxError, ValueError):
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


class FilterConditionPriorityField(FilterConditionField):
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


class FilterConditionPlaceField(FilterConditionField):
    def __init__(self, field):
        self.field = FilterConditionFieldsEnum.place
        self.entity_name = 'place.qcode'
        self.field_type = str

    def get_value(self, article):
        return [c['qcode'] for c in article[self.field.name]]


class FilterConditionIngestProviderField(FilterConditionField):
    def __init__(self, field):
        self.field = FilterConditionFieldsEnum.ingest_provider
        self.entity_name = 'ingest_provider'
        self.field_type = str


class FilterConditionEmbargoField(FilterConditionField):
    def __init__(self, field):
        self.field = FilterConditionFieldsEnum.embargo
        self.entity_name = 'embargo'
        self.field_type = bool

    def is_in_article(self, article):
        return article.get('embargo')

    def get_value(self, article):
        if article.get('embargo'):
            utc_embargo = article.get('schedule_settings', {}).get('utc_embargo')
            if utc_embargo and utc_embargo > utcnow():
                return str(True)
        return str(False)

    def get_elastic_query(self):
        return {'range': {'schedule_settings.utc_embargo': {'gt': utcnow().isoformat()}}}

    def get_mongo_query(self):
        return {'schedule_settings.utc_embargo': {'$gt': utcnow()}}


class FilterConditionControlledVocabularyField(FilterConditionField):
    def __init__(self, field):
        self.field = type('_ControlledVocabulary', (object,), {'name': field})()
        self.entity_name = 'subject.qcode'
        self.field_type = str

    def is_in_article(self, article):
        return any([self.field.name == subject.get('scheme') for subject in article.get('subject', [])])

    def get_value(self, article):
        return [s['qcode'] for s in article['subject']]


class FilterConditionCustomTextField(FilterConditionField):
    def __init__(self, field):
        self.field = type('_CustomTextField', (object,), {'name': field})()
        self.entity_name = 'extra'
        self.field_type = str

    def is_in_article(self, article):
        return self.field.name in article.get('extra', {})

    def get_value(self, article):
        return article['extra'].get(self.field.name, '')


class FilterConditionFeatureMediaField(FilterConditionField):
    def __init__(self, field):
        self.field = FilterConditionFieldsEnum.featuremedia
        self.entity_name = 'associations.featuremedia._id'
        self.field_type = bool

    def get_value(self, article):
        return ((article.get('associations') or {}).get('featuremedia') or {}).get('_id')

    def is_in_article(self, article):
        return '_id' in ((article.get('associations') or {}).get('featuremedia') or {})

    def get_elastic_query(self):
        return {"exists": {"field": "associations.featuremedia._id"}}

    def get_mongo_query(self):
        return {'associations.featuremedia._id': {'$exists': True}}
