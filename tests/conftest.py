import pytest
from superdesk.tests import setup


@pytest.fixture
def app():
    _app = setup()
    with _app.app_context():
        yield _app
