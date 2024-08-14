from pydantic import ValidationError

from superdesk.core.resources.validators import get_field_errors_from_pydantic_validation_error
from superdesk.tests import AsyncTestCase

from .modules.users import User, UserResourceService


class ResourceValidationTest(AsyncTestCase):
    app_config = {"MODULES": ["tests.core.modules.users"]}

    def test_validate_min_max(self):
        with self.assertRaises(ValueError):
            User(id="user_1", first_name="John", last_name="Doe", score=0)

        with self.assertRaises(ValueError):
            User(id="user_1", first_name="John", last_name="Doe", score=101)
        User(
            id="user_1",
            first_name="John",
            last_name="Doe",
            score=1,
        )
        User(
            id="user_1",
            first_name="John",
            last_name="Doe",
            score=100,
        )

        # Test list of values and validation errors
        with self.assertRaises(ValueError):
            User(id="user_1", first_name="John", last_name="Doe", scores=[0])

        with self.assertRaises(ValueError):
            User(id="user_1", first_name="John", last_name="Doe", scores=[101])

        with self.assertRaises(ValueError):
            User(id="user_1", first_name="John", last_name="Doe", scores=[1, 2, 3, 4, 5, -1])

        with self.assertRaises(ValueError):
            User(id="user_1", first_name="John", last_name="Doe", scores=[1, 2, 3, 4, 5, 101])

        User(id="user_1", first_name="John", last_name="Doe", scores=[1, 5, 99, 100])

    def test_validate_email(self):
        with self.assertRaises(ValueError):
            User(id="user_1", first_name="John", last_name="Doe", email="incorrect email")
        User(
            id="user_1",
            first_name="John",
            last_name="Doe",
            email="john@doe.org",
        )

    async def test_validate_data_relation(self):
        with self.assertRaises(ValueError):
            await User(
                id="user_2",
                first_name="Jane",
                last_name="Doe",
                created_by="user_1",
                updated_by="user_1",
            ).validate_async()

        service = UserResourceService()
        await service.create(
            [
                User(
                    id="user_1",
                    first_name="John",
                    last_name="Doe",
                )
            ]
        )
        await User(
            id="user_2",
            first_name="Jane",
            last_name="Doe",
            created_by="user_1",
            updated_by="user_1",
        ).validate_async()

    async def test_validate_unique_value(self):
        """Test unique value, case-sensitive"""

        service = UserResourceService()
        await service.create([User(id="user_1", first_name="John", last_name="Doe", username="John.Doe")])
        with self.assertRaises(ValueError):
            await User(id="user_2", first_name="Jane", last_name="Doe", username="John.Doe").validate_async()

        await User(id="user_2", first_name="Jane", last_name="Doe", username="john.doe").validate_async()

    async def test_validate_iunique_value(self):
        """Test unique value, case-insensitive"""

        service = UserResourceService()
        await service.create(
            [
                User(
                    id="user_1",
                    first_name="John",
                    last_name="Doe",
                    email="john@doe.org",
                )
            ]
        )
        with self.assertRaises(ValueError):
            await User(
                id="user_2",
                first_name="Jane",
                last_name="Doe",
                email="John@Doe.org",
            ).validate_async()

        await User(
            id="user_2",
            first_name="Jane",
            last_name="Doe",
            email="jane@doe.org",
        ).validate_async()

    def test_convert_validation_error_to_dict(self):
        self.maxDiff = None

        try:
            User(id="user_1", first_name="John", last_name="Doe", email="incorrect email")
        except ValidationError as error:
            issues = get_field_errors_from_pydantic_validation_error(error)
            self.assertEqual(issues, dict(email=dict(email="Invalid email address")))

        try:
            User(id="user_1", first_name="John", last_name="Doe", related_items=[])
        except ValidationError as error:
            issues = get_field_errors_from_pydantic_validation_error(error)
            self.assertEqual(
                issues,
                {
                    "related_items.0._id": dict(required="Field is required"),
                    "related_items.0.link_type": dict(required="Field is required"),
                    "related_items.0.slugline": dict(required="Field is required"),
                },
            )

    async def test_convert_validation_error_to_dict_async(self):
        service = UserResourceService()
        await service.create([User(id="user_1", first_name="John", last_name="Doe", username="John.Doe")])

        try:
            await User(id="user_2", first_name="Jane", last_name="Doe", username="John.Doe").validate_async()
        except ValidationError as error:
            print(error)
            issues = get_field_errors_from_pydantic_validation_error(error)
            self.assertEqual(issues, dict(username=dict(unique="Value must be unique")))
