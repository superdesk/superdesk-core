import unittest
from unittest.mock import patch
from pathlib import Path

from superdesk.backend_meta import backend_meta


class BackendMetaTestCase(unittest.TestCase):
    @patch.object(backend_meta, "config", object)
    def test_get_commit_href(self):
        href = backend_meta.BackendMetaService.get_commit_href("superdesk", "xyz")
        self.assertEqual(href, "https://github.com/superdesk/superdesk/commit/xyz")

    @patch.object(backend_meta.config, "REPO_OVERRIDE", {"superdesk": "superdesk-test"}, create=True)
    def test_get_commit_href_override(self):
        href = backend_meta.BackendMetaService.get_commit_href("superdesk", "xyz")
        self.assertEqual(href, "https://github.com/superdesk/superdesk-test/commit/xyz")

    @patch.object(backend_meta, "pkg_version")
    def test_get_package_version_dev(self, pkg_version):
        pkg_version.return_value = "2.0.123.dev123+g01abcde"
        version_data = backend_meta.BackendMetaService.get_package_version("superdesk-core")
        self.assertEqual(
            version_data,
            {
                "name": "superdesk-core",
                "version": "2.0.123.dev123+g01abcde",
                "semver": "2.0.123",
                "revision": "01abcde",
                "href": "https://github.com/superdesk/superdesk-core/commit/01abcde",
            },
        )

    @patch.object(backend_meta, "pkg_version")
    def test_get_package_version_stable(self, pkg_version):
        pkg_version.return_value = "2.0.123"
        version_data = backend_meta.BackendMetaService.get_package_version("superdesk-core")
        self.assertEqual(
            version_data,
            {
                "name": "superdesk-core",
                "version": "2.0.123",
                "semver": "2.0.123",
                "href": "https://pypi.org/project/superdesk-core/2.0.123/",
            },
        )

    @patch.object(backend_meta.BackendMetaService, "find_dir")
    def test_get_nodemod_version_rev(self, find_dir):
        fixtures_path = Path(__file__).parent / "fixtures" / "backend_meta" / "dev"
        find_dir.return_value = fixtures_path
        backend_meta_service = backend_meta.BackendMetaService()
        version_data = backend_meta_service.get_nodemod_version("superdesk-core", repo="superdesk-client-core")
        self.assertEqual(
            version_data,
            {
                "name": "superdesk-client-core",
                "version": "141474f6643473dee1c6794989e9b231daf13465",
                "revision": "141474f6643473dee1c6794989e9b231daf13465",
                "href": "https://github.com/superdesk/superdesk-client-core/commit/141474f6643473dee1c6794989e9b231daf13465",
            },
        )

    @patch.object(backend_meta.BackendMetaService, "find_dir")
    def test_get_nodemod_version_stable(self, find_dir):
        fixtures_path = Path(__file__).parent / "fixtures" / "backend_meta" / "stable"
        find_dir.return_value = fixtures_path
        backend_meta_service = backend_meta.BackendMetaService()
        version_data = backend_meta_service.get_nodemod_version("superdesk-core", repo="superdesk-client-core")
        self.assertEqual(
            version_data,
            {
                "name": "superdesk-client-core",
                "version": "2.1.0",
                "semver": "2.1.0",
                "href": "https://www.npmjs.com/package/superdesk-core/v/2.1.0",
            },
        )
