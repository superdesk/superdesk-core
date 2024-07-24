from superdesk.tests.asyncio import AsyncTestCase

from .modules.users import User, Category, UserResourceService


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
