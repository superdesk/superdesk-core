# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from enum import Enum, unique


@unique
class ConceptNature(Enum):
    """
    Concept items types agreed by the IPTC

    http://cv.iptc.org/newscodes/cpnature/
    """

    ABSTRACT = 'cpnat:abstract'
    EVENT = 'cpnat:event'
    GEOAREA = 'cpnat:geoArea'
    OBJECT = 'cpnat:object'
    ORGANISATION = 'cpnat:organisation'
    PERSON = 'cpnat:person'
    POI = 'cpnat:poi'

    @classmethod
    def values(cls):
        return [i.value for i in cls]
