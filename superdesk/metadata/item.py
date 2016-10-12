# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from collections import namedtuple
from superdesk.resource import Resource
from .packages import PACKAGE_TYPE, TAKES_PACKAGE, LINKED_IN_PACKAGES, PACKAGE
from eve.utils import config
from superdesk.utils import SuperdeskBaseEnum

not_analyzed = {'type': 'string', 'index': 'not_analyzed'}
not_indexed = {'type': 'string', 'index': 'no'}
GUID_TAG = 'tag'
GUID_FIELD = 'guid'
GUID_NEWSML = 'newsml'
INGEST_ID = 'ingest_id'
FAMILY_ID = 'family_id'

#: item public states
pub_status = ['usable', 'withhold', 'canceled']
PUB_STATUS = namedtuple('PUBSTATUS', ['USABLE', 'HOLD', 'CANCELED'])(*pub_status)

ITEM_TYPE = 'type'
content_type = ['text', 'preformatted', 'audio', 'video', 'picture', 'graphic', 'composite']
CONTENT_TYPE = namedtuple('CONTENT_TYPE',
                          ['TEXT', 'PREFORMATTED', 'AUDIO', 'VIDEO',
                           'PICTURE', 'GRAPHIC', 'COMPOSITE'])(*content_type)

MEDIA_TYPES = ('audio', 'video', 'picture', 'graphic')

ITEM_STATE = 'state'
ITEM_PRIORITY = 'priority'
ITEM_URGENCY = 'urgency'

#: item internal states
content_state = ['draft', 'ingested', 'routed', 'fetched', 'submitted', 'in_progress', 'spiked',
                 'published', 'killed', 'corrected', 'scheduled', 'on_hold']
CONTENT_STATE = namedtuple('CONTENT_STATE', ['DRAFT', 'INGESTED', 'ROUTED', 'FETCHED', 'SUBMITTED', 'PROGRESS',
                                             'SPIKED', 'PUBLISHED', 'KILLED', 'CORRECTED',
                                             'SCHEDULED', 'HOLD'])(*content_state)
PUBLISH_STATES = {CONTENT_STATE.PUBLISHED, CONTENT_STATE.SCHEDULED, CONTENT_STATE.CORRECTED, CONTENT_STATE.KILLED}

FORMAT = 'format'
formats = ['HTML', 'preserved']
FORMATS = namedtuple('FORMAT', ['HTML', 'PRESERVED'])(*formats)

BYLINE = 'byline'
SIGN_OFF = 'sign_off'
EMBARGO = 'embargo'
PUBLISH_SCHEDULE = 'publish_schedule'
SCHEDULE_SETTINGS = 'schedule_settings'

metadata_schema = {
    config.ID_FIELD: {
        'type': 'string',
        'unique': True
    },
    #: Identifiers
    'guid': {
        'type': 'string',
        'unique': True,
        'mapping': not_analyzed
    },
    'unique_id': {
        'type': 'integer',
        'unique': True,
    },
    'unique_name': {
        'type': 'string',
        'unique': True,
        'mapping': not_analyzed
    },
    'version': {
        'type': 'integer'
    },
    'ingest_id': {
        'type': 'string',
        'mapping': not_analyzed
    },
    'family_id': {
        'type': 'string',
        'mapping': not_analyzed
    },
    'related_to': {  # this field keeps a reference to the related item from which metadata has been copied
        'type': 'string',
        'mapping': not_analyzed
    },

    # Audit Information
    'original_creator': Resource.rel('users'),
    'version_creator': Resource.rel('users'),
    'firstcreated': {
        'type': 'datetime'
    },
    'versioncreated': {
        'type': 'datetime'
    },

    # Ingest Details
    'ingest_provider': Resource.rel('ingest_providers'),
    'source': {     # The value is copied from the ingest_providers vocabulary
        'type': 'string',
        'mapping': not_analyzed
    },
    'original_source': {    # This value is extracted from the ingest
        'type': 'string',
        'mapping': not_analyzed
    },
    'ingest_provider_sequence': {
        'type': 'string',
        'mapping': not_analyzed
    },
    # Copyright Information
    'usageterms': {
        'type': 'string',
        'nullable': True,
    },
    'copyrightnotice': {
        'type': 'string',
        'nullable': True
    },
    'copyrightholder': {
        'type': 'string',
        'nullable': True
    },
    # Category Details
    'anpa_category': {
        'type': 'list',
        'nullable': True,
        'mapping': {
            'type': 'object',
            'properties': {
                'qcode': not_analyzed,
                'name': not_analyzed,
            }
        }
    },

    'subject': {
        'type': 'list',
        'mapping': {
            'properties': {
                'qcode': not_analyzed,
                'name': not_analyzed
            }
        }
    },
    'genre': {
        'type': 'list',
        'nullable': True,
        'mapping': {
            'type': 'object',
            'properties': {
                'name': not_analyzed,
                'qcode': not_analyzed
            }
        }
    },
    'company_codes': {
        'type': 'list',
        'mapping': {
            'type': 'object',
            'properties': {
                'qcode': not_analyzed,
                'name': not_analyzed,
                'security_exchange': not_analyzed
            }
        }
    },

    # Item Metadata
    ITEM_TYPE: {
        'type': 'string',
        'allowed': content_type,
        'default': 'text',
        'mapping': not_analyzed
    },
    PACKAGE_TYPE: {
        'type': 'string',
        'allowed': [TAKES_PACKAGE]
    },
    'language': {
        'type': 'string',
        'mapping': not_analyzed,
        'nullable': True,
    },
    'abstract': {
        'type': 'string',
        'nullable': True,
    },
    'headline': {
        'type': 'string'
    },
    'slugline': {
        'type': 'string',
        'mapping': {
            'type': 'string',
            'fields': {
                'phrase': {
                    'type': 'string',
                    'analyzer': 'phrase_prefix_analyzer',
                    'search_analyzer': 'phrase_prefix_analyzer'
                }
            }
        }
    },
    'anpa_take_key': {
        'type': 'string',
        'nullable': True,
    },
    'correction_sequence': {
        'type': 'integer',
        'mapping': not_analyzed
    },
    'rewrite_sequence': {
        'type': 'integer',
        'mapping': not_analyzed
    },
    'keywords': {
        'type': 'list',
        'mapping': {
            'type': 'string'
        }
    },
    'word_count': {
        'type': 'integer'
    },
    'priority': {
        'type': 'integer',
        'nullable': True
    },
    'urgency': {
        'type': 'integer',
        'nullable': True
    },
    'profile': {
        'type': 'string',
        'nullable': True
    },

    # Related to state of an article
    ITEM_STATE: {
        'type': 'string',
        'allowed': content_state,
        'mapping': not_analyzed,
    },
    # The previous state the item was in before for example being spiked, when un-spiked it will revert to this state
    'revert_state': {
        'type': 'string',
        'allowed': content_state,
        'mapping': not_analyzed,
    },
    'pubstatus': {
        'type': 'string',
        'allowed': pub_status,
        'default': PUB_STATUS.USABLE,
        'mapping': not_analyzed,
        'nullable': True,
    },
    'signal': {
        'type': 'string',
        'mapping': not_analyzed
    },

    BYLINE: {
        'type': 'string',
        'nullable': True,
    },
    'ednote': {
        'type': 'string',
        'nullable': True,
    },
    'description_text': {
        'type': 'string',
        'nullable': True
    },
    'groups': {
        'type': 'list',
        'minlength': 1,
        'nullable': True,
    },
    'body_html': {
        'type': 'string',
        'nullable': True,
    },
    'body_text': {
        'type': 'string',
        'nullable': True,
    },
    'dateline': {
        'type': 'dict',
        'nullable': True,
        'schema': {
            'located': {'type': 'dict', 'nullable': True},
            'date': {'type': 'datetime', 'nullable': True},
            'source': {'type': 'string'},
            'text': {'type': 'string', 'nullable': True}
        },
    },
    'expiry': {
        'type': 'datetime'
    },

    # Media Related
    'media': {
        'type': 'file'
    },
    'mimetype': {
        'type': 'string',
        'mapping': not_analyzed
    },
    'poi': {
        'type': 'dict',
        'schema': {
            'x': {'type': 'float', 'nullable': False},
            'y': {'type': 'float', 'nullable': False}
        },
    },
    'renditions': {
        'type': 'dict'
    },
    'filemeta': {
        'type': 'dict'
    },
    'filemeta_json': {
        'type': 'string'
    },
    'media_file': {
        'type': 'string'
    },
    'contents': {
        'type': 'list'
    },
    'associations': {
        'type': 'dict',
    },
    'alt_text': {
        'type': 'string',
        'nullable': True
    },

    # aka Locator as per NewML Specification
    'place': {
        'type': 'list',
        'nullable': True
    },

    # Not Categorized
    'creditline': {
        'type': 'string'
    },
    LINKED_IN_PACKAGES: {
        'type': 'list',
        'readonly': True,
        'schema': {
            'type': 'dict',
            'schema': {
                PACKAGE: Resource.rel('archive'),
                PACKAGE_TYPE: {
                    'type': 'string',
                    'allowed': [TAKES_PACKAGE]
                }
            }
        }
    },
    'highlight': Resource.rel('highlights'),
    'highlights': {
        'type': 'list',
        'schema': Resource.rel('highlights', True)
    },

    'more_coming': {'type': 'boolean'},  # deprecated

    # Field which contains all the sign-offs done on this article, eg. twd/jwt/ets
    SIGN_OFF: {
        'type': 'string',
        'nullable': True,
    },

    # Desk and Stage Details
    'task': {'type': 'dict'},

    # Task and Lock Details
    'task_id': {
        'type': 'string',
        'mapping': not_analyzed,
        'versioned': False
    },

    'lock_user': Resource.rel('users'),
    'lock_time': {
        'type': 'datetime',
        'versioned': False
    },
    'lock_session': Resource.rel('auth'),

    # template used to create an item
    'template': Resource.rel('content_templates'),

    'body_footer': {  # Public Service Announcements
        'type': 'string',
        'nullable': True,
        'mapping': not_indexed,
    },

    'flags': {
        'type': 'dict',
        'schema': {
            'marked_for_not_publication': {
                'type': 'boolean',
                'default': False
            },
            'marked_for_legal': {
                'type': 'boolean',
                'default': False
            },
            'marked_archived_only': {
                'type': 'boolean',
                'default': False
            },
            'marked_for_sms': {
                'type': 'boolean',
                'default': False
            }
        }
    },

    'sms_message': {
        'type': 'string',
        'mapping': not_analyzed,
        'nullable': True
    },

    FORMAT: {
        'type': 'string',
        'mapping': not_analyzed,
        'default': FORMATS.HTML
    },

    # True indicates that the item has been or is to be published as a result of a routing rule
    'auto_publish': {
        'type': 'boolean'
    }
}

metadata_schema['lock_user']['versioned'] = False
metadata_schema['lock_session']['versioned'] = False

crop_schema = {
    'CropLeft': {'type': 'integer'},
    'CropRight': {'type': 'integer'},
    'CropTop': {'type': 'integer'},
    'CropBottom': {'type': 'integer'}
}


class Priority(SuperdeskBaseEnum):
    """Priority values."""

    Flash = 1
    Urgent = 2
    Three_Paragraph = 3
    Screen_Finance = 4
    Continuous_News = 5
    Ordinary = 6
