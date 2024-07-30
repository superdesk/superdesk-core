from superdesk.factory.app import SuperdeskEve
from flask_babel import Babel

from .validate import ValidateService


def test_validate_service_get_error_field_name():
    settings = {"DOMAIN": {}}
    app = SuperdeskEve(settings=settings)
    Babel(app)
    service = ValidateService()
    with app.app_context():
        assert service.get_error_field_name("headline") == "Headline"
        assert service.get_error_field_name("foo") == "foo"
