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
from superdesk.resource import Resource, not_analyzed, not_indexed, not_enabled
from .packages import LINKED_IN_PACKAGES, PACKAGE
from eve.utils import config
from superdesk.utils import SuperdeskBaseEnum

GUID_TAG = 'tag'
GUID_FIELD = 'guid'
GUID_NEWSML = 'newsml'
INGEST_ID = 'ingest_id'
INGEST_VERSION = 'ingest_version'
FAMILY_ID = 'family_id'
ASSOCIATIONS = 'associations'


#: item public states
pub_status = ['usable', 'withheld', 'canceled']
PUB_STATUS = namedtuple('PUBSTATUS', ['USABLE', 'HOLD', 'CANCELED'])(*pub_status)

ITEM_TYPE = 'type'
content_type = ['text', 'preformatted', 'audio', 'video', 'picture', 'graphic', 'composite', 'event']
CONTENT_TYPE = namedtuple('CONTENT_TYPE',
                          ['TEXT', 'PREFORMATTED', 'AUDIO', 'VIDEO',
                           'PICTURE', 'GRAPHIC', 'COMPOSITE', 'EVENT'])(*content_type)

MEDIA_TYPES = ('audio', 'video', 'picture', 'graphic')

ITEM_STATE = 'state'
ITEM_PRIORITY = 'priority'
ITEM_URGENCY = 'urgency'

#: item internal states
content_state = ['draft', 'ingested', 'routed', 'fetched', 'submitted', 'in_progress', 'spiked',
                 'published', 'killed', 'corrected', 'scheduled', 'recalled', 'unpublished']
CONTENT_STATE = namedtuple('CONTENT_STATE', ['DRAFT', 'INGESTED', 'ROUTED', 'FETCHED', 'SUBMITTED', 'PROGRESS',
                                             'SPIKED', 'PUBLISHED', 'KILLED', 'CORRECTED',
                                             'SCHEDULED', 'RECALLED', 'UNPUBLISHED'])(*content_state)
PUBLISH_STATES = {
    CONTENT_STATE.PUBLISHED,
    CONTENT_STATE.SCHEDULED,
    CONTENT_STATE.CORRECTED,
    CONTENT_STATE.KILLED,
    CONTENT_STATE.RECALLED,
    CONTENT_STATE.UNPUBLISHED,
}

FORMAT = 'format'
formats = ['HTML', 'preserved']
FORMATS = namedtuple('FORMAT', ['HTML', 'PRESERVED'])(*formats)

BYLINE = 'byline'
SIGN_OFF = 'sign_off'
EMBARGO = 'embargo'
PUBLISH_SCHEDULE = 'publish_schedule'
SCHEDULE_SETTINGS = 'schedule_settings'
PROCESSED_FROM = 'processed_from'

# part the task dict
LAST_DESK = 'last_desk'
LAST_AUTHORING_DESK = 'last_authoring_desk'
LAST_PRODUCTION_DESK = 'last_production_desk'
DESK_HISTORY = 'desk_history'

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
    'uri': {
        'type': 'string',
        'mapping': not_analyzed,
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
    'ingest_version': {
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
    'firstpublished': {
        'type': 'datetime',
        'required': False,
        'nullable': True,
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
        'nullable': True,
        'mapping': not_indexed
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
            'type': 'object',
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
    'package_type': {  # deprecated
        'type': 'string',
        'allowed': ['takes']
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
        'type': 'list',
        'mapping': {
            'type': 'object',
            'properties': {
                'qcode': not_analyzed,
                'name': not_analyzed,
                'scheme': not_analyzed
            }
        }
    },

    BYLINE: {
        'type': 'string',
        'nullable': True,
    },
    'ednote': {
        'type': 'string',
        'nullable': True,
    },
    'authors': {
        'type': 'list',
        'nullable': True,
        'mapping': {
            'type': 'object',
            'dynamic': False,
            'properties': {
                'uri': not_analyzed,
                'parent': not_analyzed,
                'name': not_analyzed,
                'role': not_analyzed,
                'jobtitle': not_enabled,
            }
        }
    },
    'description_text': {
        'type': 'string',
        'nullable': True
    },
    # This is a description of the item as recieved from its source.
    'archive_description': {
        'type': 'string',
        'nullable': True
    },
    'groups': {
        'type': 'list',
        'minlength': 1,
        'nullable': True,
    },
    'deleted_groups': {
        'type': 'list',
        'minlength': 1,
        'nullable': True,
    },
    'body_html': {
        'type': 'string',
        'nullable': True,
        'mapping': {
            'type': 'string',
            'analyzer': 'html_field_analyzer',
            'search_analyzer': 'standard'
        }
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
    ASSOCIATIONS: {
        'type': 'dict',
        'mapping': {
            'type': 'object',
            'dynamic': False,
            'properties': {
                'featuremedia': {  # keep indexing featuremedia - we do some filtering using it
                    'type': 'object',
                    'dynamic': False,
                    'properties': {
                        '_id': not_analyzed,
                        'guid': not_analyzed,
                        'unique_id': {'type': 'integer'},
                    }
                }
            }
        }
    },
    'alt_text': {
        'type': 'string',
        'nullable': True
    },

    # aka Locator as per NewML Specification
    'place': {
        'type': 'list',
        'nullable': True,
        'mapping': {
            'type': 'object',
            'dynamic': False,
            'properties': {
                'scheme': not_analyzed,
                'qcode': not_analyzed,
                'code': not_analyzed,  # content api
                'name': not_analyzed,
                'locality': not_analyzed, # can be used for city/town/village etc.
                'state': not_analyzed,
                'country': not_analyzed,
                'world_region': not_analyzed,
                'locality_code': not_analyzed,
                'state_code': not_analyzed,
                'country_code': not_analyzed,
                'world_region_code': not_analyzed,
                'feature_class': not_analyzed,
                'location': {'type': 'geo_point'},
                'rel': not_analyzed,
            },
        },
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
                'package_type': {  # deprecated
                    'type': 'string'
                }
            }
        }
    },
    'highlight': Resource.rel('highlights'),
    'highlights': {
        'type': 'list',
        'schema': Resource.rel('highlights', True)
    },
    'marked_desks': {
        'type': 'list',
        'nullable': True,
        'schema': {
            'type': 'dict',
            'schema': {
                'desk_id': Resource.rel('desks', True),
                'date_marked': {'type': 'datetime', 'nullable': True},
                'user_marked': Resource.rel('users', required=False, nullable=True),
                'date_acknowledged': {'type': 'datetime', 'nullable': True},
                'user_acknowledged': Resource.rel('users', required=False, nullable=True)
            }
        },
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

    # Action when the story is locked: edit, correct, kill
    'lock_action': {
        'type': 'string',
        'mapping': not_analyzed,
        'nullable': True
    },

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
    },

    # draft-js internal data
    'fields_meta': {
        'type': 'dict',
        'nullable': True,
        'mapping': not_enabled,
    },

    'annotations': {
        'type': 'list',
        'mapping': not_enabled,
        'schema': {
            'type': 'dict',
            'schema': {
                'id': {'type': 'integer'},
                'type': {'type': 'string'},
                'body': {'type': 'string'},
            },
        },
    },

    'extra': {
        'type': 'dict',
        'mapping': not_enabled,
    },

    'attachments': {
        'type': 'list',
        'nullable': True,
        'schema': {
            'type': 'dict',
            'schema': {
                'attachment': Resource.rel('attachments', nullable=False),
            },
        },
    },

    # references assignment related to the coverage
    'assignment_id': {
        'type': 'string',
        'mapping': not_analyzed
    },

    "translated_from": {
        'type': 'string',
        'mapping': not_analyzed,
    },

    'translation_id': {
        'type': 'string',
        'mapping': not_analyzed,
    },

    'translations': {
        'type': 'list',
        'mapping': not_analyzed,
    },

    # references item id for items auto published using internal destinations
    PROCESSED_FROM: {'type': 'string', 'mapping': not_analyzed},

    # ingested embargoed info, not using embargo to avoid validation
    'embargoed': {'type': 'datetime'},
    'embargoed_text': {'type': 'string', 'mapping': not_indexed},

    'marked_for_user': Resource.rel('users', required=False, nullable=True)
}

metadata_schema['lock_user']['versioned'] = False
metadata_schema['lock_session']['versioned'] = False

crop_schema = {
    'CropLeft': {'type': 'integer'},
    'CropRight': {'type': 'integer'},
    'CropTop': {'type': 'integer'},
    'CropBottom': {'type': 'integer'}
}


def remove_metadata_for_publish(item):
    """Remove metadata from item that should not be public.

    :param item: Item containing the metadata
    :return: item
    """
    from superdesk.attachments import is_attachment_public

    if len(item.get('attachments', [])) > 0:
        item['attachments'] = [attachment for attachment in item['attachments'] if is_attachment_public(attachment)]

    return item


class Priority(SuperdeskBaseEnum):
    """Priority values."""

    Flash = 1
    Urgent = 2
    Three_Paragraph = 3
    Screen_Finance = 4
    Continuous_News = 5
    Ordinary = 6
