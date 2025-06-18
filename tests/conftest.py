import pytest
from superdesk.tests import setup


@pytest.fixture
async def app():
    _app = await setup()
    async with _app.app_context():
        yield _app
