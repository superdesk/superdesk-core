
import unittest

from superdesk.backend_meta.backend_meta import get_client_ref, get_server_ref


class BackendMetaTestCase(unittest.TestCase):

    def test_client_ref_commit(self):
        ref = get_client_ref('superdesk-client-core#b5d555fd', 'superdesk-core', 'superdesk-client-core')
        self.assertEqual('b5d555fd', ref['name'])
        self.assertEqual('https://github.com/superdesk/superdesk-client-core/commit/b5d555fd', ref['href'])

    def test_client_ref_branch(self):
        ref = get_client_ref('superdesk-client-core#master', 'superdesk-core', 'superdesk-client-core')
        self.assertEqual('master', ref['name'])
        self.assertEqual('https://github.com/superdesk/superdesk-client-core/tree/master', ref['href'])

    def test_client_ref_tag(self):
        ref = get_client_ref('1.27.0', 'superdesk-core', 'superdesk-client-core')
        self.assertEqual('1.27.0', ref['name'])
        self.assertEqual('https://github.com/superdesk/superdesk-client-core/releases/tag/v1.27.0', ref['href'])

    def test_server_ref_branch(self):
        ref = get_server_ref(
            '-e git+git://github.com/superdesk/superdesk-core.git@master#egg=Superdesk-Core',
            'superdesk-core')
        self.assertEqual('master', ref['name'])
        self.assertEqual('https://github.com/superdesk/superdesk-core/tree/master', ref['href'])

    def test_server_ref_commit(self):
        ref = get_server_ref(
            '-e git+git://github.com/superdesk/superdesk-core.git@aaaaa#egg=Superdesk-Core',
            'superdesk-core')
        self.assertEqual('aaaaa', ref['name'])
        self.assertEqual('https://github.com/superdesk/superdesk-core/commit/aaaaa', ref['href'])

    def test_server_ref_tag(self):
        ref = get_server_ref('Superdesk-Core==1.26', 'superdesk-core')
        self.assertEqual('1.26', ref['name'])
        self.assertEqual('https://github.com/superdesk/superdesk-core/releases/tag/v1.26', ref['href'])
