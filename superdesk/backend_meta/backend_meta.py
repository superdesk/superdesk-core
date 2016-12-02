# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


from superdesk.resource import Resource
from superdesk.services import BaseService
import os.path
import re
import json
try:
    import settings
except ImportError:
    # settings doesn't exist during tests
    settings = None
import logging

logger = logging.getLogger(__name__)


class BackendMetaResource(Resource):
    pass


class BackendMetaService(BaseService):
    """Service givin metadata on backend itself"""

    def find_dir(self, name):
        # depending of the installation (local git or docker)
        # a dir can be in the same path as settings or in the parent
        # this method try both and return None if dir is not found
        if settings is None:
            return
        current_path = settings.__file__
        for i in range(2):
            current_path = os.path.dirname(current_path)
            tested_dir = os.path.join(current_path, name)
            if os.path.isdir(tested_dir):
                return tested_dir

    def get_superdesk_rev(self):
        git_dir = self.find_dir('.git')
        if git_dir is not None:
            head_path = os.path.join(git_dir, 'HEAD')
            try:
                with open(head_path) as f:
                    head = f.read()
                ref_path = head.split()[1]
                with open(os.path.join(git_dir, ref_path)) as rev_f:
                    return rev_f.read()
            except (IOError, IndexError):
                pass
        return ''

    def get_core_rev(self):
        if settings is not None:
            # we get superdesk-core revision from requirements.txt
            requirements_path = os.path.join(os.path.dirname(settings.__file__), 'requirements.txt')
            try:
                with open(requirements_path) as f:
                    req = f.read()
                return re.search(r'superdesk-core.git@([0-9a-f]+)#', req).group(1)
            except (IOError, AttributeError):
                pass
        return ''

    def get_client_rev(self):
        # we get superdesk-client-core revision from package.json
        client_dir = self.find_dir('client')
        if client_dir is not None:
            pkg_path = os.path.join(client_dir, 'package.json')
            try:
                with open(pkg_path) as f:
                    pkg = json.load(f)
                return pkg['dependencies']['superdesk-core'].split('#')[-1]
            except (IOError, ValueError, KeyError, IndexError):
                pass
        return ''

    def on_fetched(self, doc):
        doc['meta_rev'] = self.get_superdesk_rev()
        doc['meta_rev_core'] = self.get_core_rev()
        doc['meta_rev_client'] = self.get_client_rev()
