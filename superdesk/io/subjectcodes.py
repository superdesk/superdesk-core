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
import superdesk
from flask import Blueprint, current_app as app
from datetime import datetime
from eve.render import send_response


bp = Blueprint('subjectcodes', __name__)


class SubjectIndex():
    """Subjects index."""

    newscode_pattern = re.compile('[0-9]{8,9}')

    def __init__(self):
        self.subjects = {}
        self.last_modified = datetime.fromtimestamp(0)

    def register(self, subjects, last_modified=None):
        """Register subjects.

        :param subjects: dict with subject qcode as key and name as value
        :param last_modified: datetime for last subjects modification, last one is sent to clients
        """
        self.subjects.update(subjects)
        if last_modified is not None:
            self.last_modified = max(self.last_modified, last_modified)

    def get_items(self):
        """Get list of all subjects.

        Each subject is a dict with `qcode`, `name` and `parent` keys.
        """
        items = []
        for code in sorted(self.subjects):
            items.append({'qcode': code, 'name': self.subjects[code], 'parent': self._get_parent_code(code)})
        return items

    def _get_parent_code(self, code):
        """Compute parent code for iptc newscode.

        :param code: iptc newscode without `subj:` prefix
        """
        parent_code = None
        if not self.newscode_pattern.match(code):
            return parent_code
        if code[-3:] != '000':
            parent_code = code[:5] + '000'
        elif code[2:5] != '000':
            parent_code = code[:2] + '000000'
        return parent_code


@bp.route('/subjectcodes/', methods=['GET', 'OPTIONS'])
def render_subjectcodes():
    items = get_subjectcodeitems()
    response_data = {'_items': items, '_meta': {'total': len(items)}}
    return send_response(None, (response_data, app.subjects.last_modified, None, 200))


def get_subjectcodeitems():
    """Get subjects for current app."""
    return app.subjects.get_items()


def init_app(app):
    app.subjects = SubjectIndex()
    superdesk.blueprint(bp)
