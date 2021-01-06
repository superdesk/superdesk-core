# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


import os.path
import re
import json
from pathlib import Path
from typing import Optional, Dict
from superdesk.resource import Resource
from superdesk.services import BaseService
from superdesk import config

try:
    import settings
except ImportError:
    # settings doesn't exist during tests
    settings = None
import logging
from importlib_metadata import version as pkg_version, PackageNotFoundError


logger = logging.getLogger(__name__)

GITHUB_TAG_HREF = "https://github.com/superdesk/{repo}/releases/tag/v{version}"
GITHUB_COMMIT_HREF = "https://github.com/superdesk/{package}/commit/{revision}"
GITHUB_BRANCH_HREF = "https://github.com/superdesk/{package}/tree/{branch}"
PYPI_VERSION_HREF = "https://pypi.org/project/{package}/{version}/"
NPM_VERSION_HREF = "https://www.npmjs.com/package/{package}/v/{version}"

RE_REV = re.compile(r"\+g(?P<revision>[a-f0-9]+)(\.[0-9]+)?")


class BackendMetaResource(Resource):
    pass


class BackendMetaService(BaseService):
    """Service givin metadata on backend itself"""

    @staticmethod
    def find_dir(name: str) -> Optional[Path]:
        """Look for a dir in up to 2 parents directories"""
        # depending of the installation (local git or docker)
        # a dir can be in the same path as settings or in the parent
        # this method try both and return None if dir is not found
        if settings is None:
            return None
        current_path = Path(settings.__file__)
        for i in range(2):
            current_path = current_path.parent
            tested_dir = current_path / name
            if tested_dir.is_dir():
                return tested_dir
        return None

    @staticmethod
    def get_commit_href(package: str, revision: str) -> str:
        """Get URL for a Github commit

        if config.REPO_OVERRIDE is set, it will be used
        """
        try:
            repo_override = config.REPO_OVERRIDE
        except AttributeError:
            # config may not be initialised (during tests or beginning of the session)
            repo_override = {}
        return GITHUB_COMMIT_HREF.format(package=repo_override.get(package, package), revision=revision)

    @classmethod
    def get_superdesk_version(cls) -> Optional[Dict[str, str]]:
        """Get version data for main superdesk package

        because superdesk is not installed as a Python package, this works by looking for GIT
        metadata and retrieving the commit version from there
        """
        git_dir = cls.find_dir(".git")
        if git_dir is not None:
            head_path = git_dir / "HEAD"
            try:
                with head_path.open() as f:
                    head = f.read()
                ref_path = head.split()[1]
                with open(os.path.join(git_dir, ref_path)) as rev_f:
                    revision = rev_f.read()
                return {
                    "name": "superdesk",
                    # we don't have semver for Superdesk itself (only for core)
                    "version": revision,
                    "revision": revision,
                    "href": cls.get_commit_href("superdesk", revision),
                }
            except (IOError, IndexError):
                pass
        return None

    @classmethod
    def get_package_version(cls, package: str) -> Optional[Dict[str, str]]:
        """Get version data for a Python package"""
        try:
            version = pkg_version(package)
        except PackageNotFoundError:
            pass
        except Exception as e:
            logger.error(f"Can't retrieve package version: {e}")
            return None
        else:
            semver = ".".join(version.split(".", 3)[:3])
            data = {
                "name": package,
                "version": version,
                "semver": semver,
            }
            rev_match = RE_REV.search(version)
            if rev_match is not None:
                revision = rev_match.group("revision")
                data["revision"] = revision
                data["href"] = cls.get_commit_href(package, revision)
            elif version == semver:
                data["href"] = PYPI_VERSION_HREF.format(
                    package=package,
                    version=semver,
                )
            return data
        return None

    def complete_nodemod_ref(self, data: Dict[str, str], package: str, repo: Optional[str] = None) -> None:
        """Complete when possible missing data for a node module version"""
        if not repo:
            repo = package
        try:
            version = data["version"]
        except KeyError:
            return
        try:
            commit = version.split("#")[1]
        except IndexError:
            if "href" not in data:
                data["href"] = GITHUB_TAG_HREF.format(repo=repo, version=version)
        else:
            if "href" not in data:
                try:
                    int(version, 16)
                    data["href"] = GITHUB_COMMIT_HREF.format(package=repo, revision=commit)
                except ValueError:
                    data["href"] = GITHUB_BRANCH_HREF.format(package=repo, branch=commit)

    def get_nodemod_version(self, package: str, repo: Optional[str] = None) -> Optional[Dict[str, str]]:
        """Get version data for a Node module"""
        # we get superdesk-client-core version and revision from package.json and package-lock.json
        client_dir = self.find_dir("client")
        if client_dir is not None:
            data = {
                "name": repo or package,
            }
            pkg_path = client_dir / "package.json"
            try:
                with pkg_path.open() as f:
                    pkg = json.load(f)
                data["version"] = pkg["dependencies"][package]
            except (IOError, KeyError):
                pass
            pkg_lock_path = client_dir / "package-lock.json"
            try:
                with pkg_lock_path.open() as f:
                    pkg_lock = json.load(f)
                pkg_ver = pkg_lock["dependencies"][package]["version"]
                if pkg_ver.startswith("github:"):
                    __, data["revision"] = pkg_ver[8:].split("#")
                    data["version"] = data["revision"]
                    data["href"] = self.get_commit_href(repo or package, data["revision"])
                else:
                    data["version"] = data["semver"] = pkg_ver
                    data["href"] = NPM_VERSION_HREF.format(package=package, version=pkg_ver)
            except (IOError, KeyError):
                self.complete_nodemod_ref(data, package, repo)

            if len(data) == 1:
                # if we have only the module name, we don't want to display it
                return None
            return data

        return None

    def on_fetched(self, doc):
        doc["modules"] = [
            mod
            for mod in [
                self.get_superdesk_version(),
                self.get_package_version("superdesk-core"),
                self.get_nodemod_version("superdesk-core", repo="superdesk-client-core"),
                self.get_package_version("superdesk-planning"),
                self.get_package_version("superdesk-analytics"),
                self.get_nodemod_version("superdesk-publisher"),
            ]
            if mod is not None
        ]


# it may be useful to have the version of installed packages in backend logs
for package in ("superdesk-core", "superdesk-planning", "superdesk-analytics", "superdesk-published"):
    v_data = BackendMetaService.get_package_version(package)
    if v_data is not None:
        logger.info(f"version of {package!r}: {v_data['version']}")
