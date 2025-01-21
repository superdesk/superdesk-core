from typing import Any
from unittest import IsolatedAsyncioTestCase, mock
from unittest.mock import Mock, AsyncMock, ANY

from superdesk.core import AsyncSignal
from superdesk.core.resources import AsyncResourceService, global_signals
from superdesk.core.resources.resource_signals import clear_all_resource_signal_listeners
from superdesk.core.types import Request, Response, SearchRequest
from superdesk.utc import utcnow
from superdesk.utils import format_time
from superdesk.factory.app import HttpFlaskRequest
from superdesk.errors import SuperdeskApiError

from superdesk.tests import AsyncTestCase, AsyncFlaskTestCase

from .modules.users import User
from .fixtures.users import john_doe

NOW = utcnow()


class AsyncSignalsTestCase(IsolatedAsyncioTestCase):
    async def test_signals(self):
        signal = AsyncSignal[str, bool]("on_some_event")

        signal_cb1 = Mock()
        signal_cb2 = AsyncMock()
        signal_cb3 = AsyncMock()

        signal += signal_cb1
        signal.connect(signal_cb2)
        signal.connect(signal_cb3)

        await signal.send("monkeys", True)
        signal_cb1.assert_called_once_with("monkeys", True)
        signal_cb2.assert_called_once_with("monkeys", True)
        signal_cb2.assert_awaited()
        signal_cb3.assert_called_once_with("monkeys", True)
        signal_cb3.assert_awaited()

        signal_cb1.reset_mock()
        signal_cb2.reset_mock()
        signal_cb3.reset_mock()

        signal -= signal_cb2
        signal.disconnect(signal_cb3)
        await signal.send("space", False)
        signal_cb1.assert_called_once_with("space", False)
        signal_cb2.assert_not_called()
        signal_cb3.assert_not_called()


class ResourceDataSignalsTestCase(AsyncTestCase):
    app_config = {"MODULES": ["tests.core.modules.users"]}
    service: AsyncResourceService[User]

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.service = User.get_service()

    async def asyncTearDown(self):
        await super().asyncTearDown()
        clear_all_resource_signal_listeners()

    async def test_clear_signal_listeners(self):
        signals = User.get_signals()
        self.assertEqual(1, len(signals.data.on_create))

        cb = AsyncMock()
        signals.data.on_create.connect(cb)
        self.assertEqual(2, len(signals.data.on_create))

        signals.clear_listeners()
        self.assertEqual(1, len(signals.data.on_create))

    async def test_data_signals(self):
        signals = User.get_signals()

        callbacks: dict[str, list[AsyncMock]] = {}
        for event in ["create", "update", "delete"]:
            name = f"on_{event}"
            callbacks[name] = [AsyncMock(name=f"resource:{name}"), AsyncMock(name=f"global:{name}")]

            getattr(signals.data, name).connect(callbacks[name][0])
            getattr(global_signals.data, name).connect(callbacks[name][1])

            name = f"on_{event}d"
            callbacks[name] = [AsyncMock(name=f"resource:{name}"), AsyncMock(name=f"global:{name}")]
            getattr(signals.data, name).connect(callbacks[name][0])
            getattr(global_signals.data, name).connect(callbacks[name][1])

        test_user = john_doe()

        def assert_mocks_called(action: str, *test_args):
            callbacks[f"on_{action}"][0].assert_called_once_with(*test_args)
            callbacks[f"on_{action}"][1].assert_called_once_with(*test_args)
            callbacks[f"on_{action}d"][0].assert_called_once_with(*test_args)
            callbacks[f"on_{action}d"][1].assert_called_once_with(*test_args)

            for callback_name, callback in callbacks.items():
                if action not in callback_name:
                    callback[0].assert_not_called()
                    callback[1].assert_not_called()

            call_count = 0
            for callback in callbacks.values():
                call_count += callback[0].call_count
                call_count += callback[1].call_count
                callback[0].reset_mock()
                callback[1].reset_mock()

            assert call_count == 4

        # Test create signals
        await self.service.create([test_user])
        assert_mocks_called("create", test_user)

        # Test update signals
        updates = dict(first_name="Foo", last_name="Bar")
        await self.service.update(test_user.id, updates)
        assert_mocks_called("update", test_user, updates)

        # Test delete signals
        await self.service.delete(test_user)
        assert_mocks_called("delete", test_user)

    async def test_modifying_data_from_data_signal(self):
        test_user = john_doe()

        def modify_on_create(user: User) -> None:
            # Test modifying the item before it's inserted into the DB
            user.code = "test_created"

        def modify_on_update(original: User, updates: dict[str, Any]) -> None:
            # Test modifying the item before it's updated in the DB
            updates["code"] = "test_updated"

        def raise_error_on_delete(user: User) -> None:
            # Test raising an error under certain conditions
            if user.code == "test_created":
                raise AttributeError("Invalid user state")

        signals = User.get_signals()
        signals.data.on_create.connect(modify_on_create)
        signals.data.on_update.connect(modify_on_update)
        signals.data.on_delete.connect(raise_error_on_delete)

        # Test modify in create signal
        await self.service.create([test_user])
        user_in_db = await self.service.find_by_id(test_user.id)
        self.assertEqual(user_in_db.code, "test_created")

        # Test exception is raised from connected signal, due to value of code field
        with self.assertRaises(AttributeError) as e:
            await self.service.delete(user_in_db)
            self.assertEqual(str(e.exception), "Invalid user state")

        # Test modify in update signal
        await self.service.update(test_user.id, dict(first_name="Foo", last_name="Bar"))
        user_in_db = await self.service.find_by_id(test_user.id)
        self.assertEqual(user_in_db.code, "test_updated")

        # Test exception IS NOT raised from connected signal, due to value of code field
        await self.service.delete(user_in_db)
        self.assertIsNone(await self.service.find_by_id(test_user.id))

        # Disconnect resource specific signals, and re-connect to global resource signals
        signals.data.on_create.disconnect(modify_on_create)
        signals.data.on_update.disconnect(modify_on_update)
        signals.data.on_delete.disconnect(raise_error_on_delete)

        global_signals.data.on_create.connect(modify_on_create)
        global_signals.data.on_update.connect(modify_on_update)
        global_signals.data.on_delete.connect(raise_error_on_delete)

        # Test modify in create signal
        await self.service.create([test_user])
        user_in_db = await self.service.find_by_id(test_user.id)
        self.assertEqual(user_in_db.code, "test_created")

        # Test exception is raised from connected signal, due to value of code field
        with self.assertRaises(AttributeError) as e:
            await self.service.delete(user_in_db)
            self.assertEqual(str(e.exception), "Invalid user state")

        # Test modify in update signal
        await self.service.update(test_user.id, dict(first_name="Foo", last_name="Bar"))
        user_in_db = await self.service.find_by_id(test_user.id)
        self.assertEqual(user_in_db.code, "test_updated")

        # Test exception IS NOT raised from connected signal, due to value of code field
        await self.service.delete(user_in_db)
        self.assertIsNone(await self.service.find_by_id(test_user.id))


class ResourceWebSignalsTestCase(AsyncFlaskTestCase):
    app_config = {"MODULES": ["tests.core.modules.users"]}
    service: AsyncResourceService[User]

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.service = User.get_service()

    async def asyncTearDown(self):
        await super().asyncTearDown()
        clear_all_resource_signal_listeners()
        # global_signals.clear_listeners()
        # User.get_signals().clear_listeners()

    @mock.patch("superdesk.core.resources.service.utcnow", return_value=NOW)
    async def test_web_signals(self, mock_utcnow):
        signals = User.get_signals()

        callbacks: dict[str, list[AsyncMock]] = {}
        for event in ["create", "update", "delete", "get", "search"]:
            name = f"on_{event}"
            callbacks[name] = [AsyncMock(), AsyncMock()]
            getattr(signals.web, name).connect(callbacks[name][0])
            getattr(global_signals.web, name).connect(callbacks[name][1])

            name = f"on_{event}_response"
            callbacks[name] = [AsyncMock(), AsyncMock()]
            getattr(signals.web, name).connect(callbacks[name][0])
            getattr(global_signals.web, name).connect(callbacks[name][1])

        def assert_mocks_called(action: str, pre_args: list[Any], post_args: list[Any]):
            callbacks[f"on_{action}"][0].assert_called_once_with(*pre_args)
            callbacks[f"on_{action}"][1].assert_called_once_with(*pre_args)
            callbacks[f"on_{action}_response"][0].assert_called_once_with(*post_args)
            callbacks[f"on_{action}_response"][1].assert_called_once_with(*post_args)

            # Assert the first argument is a request instance
            self.assertIsInstance(callbacks[f"on_{action}"][0].call_args[0][0], HttpFlaskRequest)
            self.assertIsInstance(callbacks[f"on_{action}"][1].call_args[0][0], HttpFlaskRequest)
            self.assertIsInstance(callbacks[f"on_{action}_response"][0].call_args[0][0], HttpFlaskRequest)
            self.assertIsInstance(callbacks[f"on_{action}_response"][1].call_args[0][0], HttpFlaskRequest)

            for callback_name, callback in callbacks.items():
                if action not in callback_name:
                    callback[0].assert_not_called()
                    callback[1].assert_not_called()

            call_count = 0
            for callback in callbacks.values():
                call_count += callback[0].call_count
                call_count += callback[1].call_count
                callback[0].reset_mock()
                callback[1].reset_mock()

            assert call_count == 4

        test_user = john_doe()

        # Test create signals
        response = await self.test_client.post("/api/users_async", json=test_user)
        self.assertEqual(response.status_code, 201)
        response_data = await response.get_json()
        test_user.etag = response_data["_etag"]
        test_user.created = NOW
        test_user.updated = NOW
        assert_mocks_called(
            "create",
            [ANY, [test_user]],
            [
                ANY,
                Response(
                    {
                        **test_user.to_dict(),
                        "_links": {"self": {"title": "User", "href": "users_async/user_1"}},
                    },
                    201,
                    (),
                ),
            ],
        )

        # Test get signals
        test_user = await self.service.find_by_id(test_user.id)
        response = await self.test_client.get(f"/api/users_async/{test_user.id}")
        self.assertEqual(response.status_code, 200)
        assert_mocks_called(
            "get",
            [ANY],
            [
                ANY,
                Response(
                    {
                        **test_user.to_dict(),
                        "_created": format_time(NOW) + "+00:00",
                        "_updated": format_time(NOW) + "+00:00",
                    },
                    200,
                    (),
                ),
            ],
        )

        # Test search signals
        response = await self.test_client.get("""/api/users_async?source={"query":{"match":{"first_name":"John"}}}""")
        self.assertEqual(response.status_code, 200)
        response_data = await response.get_json()
        from pprint import pprint

        pprint(response_data)
        assert_mocks_called(
            "search",
            [
                ANY,
                SearchRequest(
                    args={"source": '{"query":{"match":{"first_name":"John"}}}'},
                    source='{"query":{"match":{"first_name":"John"}}}',
                ),
            ],
            [
                ANY,
                Response(
                    {
                        "_items": [
                            {
                                **test_user.to_dict(),
                                "_created": format_time(NOW) + "+00:00",
                                "_updated": format_time(NOW) + "+00:00",
                            }
                        ],
                        "_meta": {
                            "page": 1,
                            "max_results": 25,
                            "total": 1,
                        },
                        "_links": ANY,
                    },
                    200,
                    [("X-Total-Count", 1)],
                ),
            ],
        )

        # Test update signals
        test_user = await self.service.find_by_id(test_user.id)
        response = await self.test_client.patch(
            f"/api/users_async/{test_user.id}",
            json={
                "first_name": "Foo",
                "last_name": "Bar",
            },
            headers={"If-Match": test_user.etag},
        )
        self.assertEqual(response.status_code, 200)
        response_data = await response.get_json()
        assert_mocks_called(
            "update",
            [ANY, test_user, {"first_name": "Foo", "last_name": "Bar"}],
            [
                ANY,
                Response(
                    {
                        "_id": test_user.id,
                        "_updated": NOW,
                        "_etag": response_data["_etag"],
                        "first_name": "Foo",
                        "last_name": "Bar",
                        "_status": "OK",
                        "_links": {"self": {"title": "User", "href": "users_async/user_1"}},
                    },
                    200,
                    (),
                ),
            ],
        )

        # Test delete signals
        test_user = await self.service.find_by_id(test_user.id)
        response = await self.test_client.delete(
            f"/api/users_async/{test_user.id}", headers={"If-Match": test_user.etag}
        )
        self.assertEqual(response.status_code, 204)
        assert_mocks_called("delete", [ANY, test_user], [ANY, Response({}, 204, ())])

    async def test_modifying_data_from_web_signal(self):
        test_user = john_doe()

        def modify_on_create(request: Request, users: list[User]) -> None:
            # Test modifying the item before it's inserted into the DB
            users[0].code = "test_created"

        def modify_on_update(request: Request, original: User, updates: dict[str, Any]) -> None:
            # Test modifying the item before it's updated in the DB
            updates["code"] = "test_updated"

        def raise_error_on_delete(request: Request, user: User) -> None:
            # Test raising an error under certain conditions
            if user.code == "test_created":
                raise SuperdeskApiError.badRequestError("Invalid user state")

        signals = User.get_signals()
        signals.web.on_create.connect(modify_on_create)
        signals.web.on_update.connect(modify_on_update)
        signals.web.on_delete.connect(raise_error_on_delete)

        # Test modify in create signal
        response = await self.test_client.post("/api/users_async", json=test_user)
        self.assertEqual(response.status_code, 201)
        user_in_db = await self.service.find_by_id(test_user.id)
        self.assertEqual(user_in_db.code, "test_created")

        # Test exception is raised from connected signal, due to value of code field
        response = await self.test_client.delete(
            f"/api/users_async/{test_user.id}", headers={"If-Match": user_in_db.etag}
        )
        self.assertEqual(response.status_code, 400)
        self.assertTrue("Invalid user state" in await response.get_data(as_text=True))

        # Test modify in update signal
        response = await self.test_client.patch(
            f"/api/users_async/{user_in_db.id}",
            json={
                "first_name": "Foo",
                "last_name": "Bar",
            },
            headers={"If-Match": user_in_db.etag},
        )
        self.assertEqual(response.status_code, 200)
        user_in_db = await self.service.find_by_id(test_user.id)
        self.assertEqual(user_in_db.code, "test_updated")

        # Test exception IS NOT raised from connected signal, due to value of code field
        response = await self.test_client.delete(
            f"/api/users_async/{test_user.id}", headers={"If-Match": user_in_db.etag}
        )
        self.assertEqual(response.status_code, 204)
        self.assertIsNone(await self.service.find_by_id(test_user.id))
