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

GITHUB_TAG_HREF = 'https://github.com/superdesk/%s/releases/tag/v%s'
GITHUB_COMMIT_HREF = 'https://github.com/superdesk/%s/commit/%s'
GITHUB_BRANCH_HREF = 'https://github.com/superdesk/%s/tree/%s'


def get_client_ref(version, package, repo=None):
    if not repo:
        repo = package
    try:
        commit = version.split('#')[1]
        try:
            int(commit, 16)
            template = GITHUB_COMMIT_HREF
        except ValueError:
            template = GITHUB_BRANCH_HREF
        return {
            'name': repo,
            'href': template % (repo, commit),
            'version': commit,
        }
    except IndexError:
        pass
    return {
        'name': repo,
        'href': GITHUB_TAG_HREF % (repo, version),
        'version': version,
    }


def get_server_ref(req, package):
    try:
        version = re.search(r'%s==([0-9.]+)' % package, req, re.IGNORECASE).group(1)
        return {
            'name': package,
            'href': GITHUB_TAG_HREF % (package, version),
            'version': version,
        }
    except AttributeError:
        pass
    try:
        commit = re.search(r'%s.git@([-.a-z0-9]+)#' % package, req, re.IGNORECASE).group(1)  # branch or commit
        try:
            int(commit, 16)
            template = GITHUB_COMMIT_HREF
        except ValueError:
            template = GITHUB_BRANCH_HREF
        return {
            'name': package,
            'href': template % (package, commit),
            'version': commit,
        }
    except AttributeError:
        pass


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
        return None

    def get_server_rev(self, package):
        if settings is not None:
            # we get superdesk-core revision from requirements.txt
            requirements_path = os.path.join(os.path.dirname(settings.__file__), 'requirements.txt')
            try:
                with open(requirements_path) as f:
                    req = f.read()
                    return get_server_ref(req, package)
            except IOError:
                pass
        return None

    def get_client_rev(self, package, repo=None):
        # we get superdesk-client-core revision from package.json
        client_dir = self.find_dir('client')
        if client_dir is not None:
            pkg_path = os.path.join(client_dir, 'package.json')
            try:
                with open(pkg_path) as f:
                    pkg = json.load(f)
                version = pkg['dependencies'][package]
                return get_client_ref(version, package, repo)
            except (IOError, KeyError):
                pass
        return None

    def on_fetched(self, doc):
        doc['meta_rev'] = self.get_superdesk_rev()
        doc['modules'] = [mod for mod in [
            self.get_server_rev('superdesk-core'),
            self.get_client_rev('superdesk-core', repo='superdesk-client-core'),
            self.get_server_rev('superdesk-planning'),
            self.get_server_rev('superdesk-analytics'),
            self.get_client_rev('superdesk-publisher'),
        ] if mod is not None]
