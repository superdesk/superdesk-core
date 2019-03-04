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
from superdesk.text_utils import get_text

p = re.compile('(?i)(?<=[.?!])\\S+(?=[a-z])')


def populate(item, **kwargs):
    """Populate the abstract field with the first sentence of the body"""

    # get the list of sentences of the body
    if not item.get('body_html', None):
        item['abstract'] = 'No body found to use for abstract...'
    else:
        sentences = p.split(item['body_html'])

        # chop the first sentence to size for abstract (64)
        if sentences and len(sentences) > 0:
            item['abstract'] = get_text(sentences[0][:64]).strip()

    return item


name = 'populate_abstract'
label = 'Populate Abstract'
order = 3
shortcut = 'a'
callback = populate
desks = ['POLITICS']
access_type = 'frontend'
action_type = 'direct'
replace_type = 'keep-style-replace'
