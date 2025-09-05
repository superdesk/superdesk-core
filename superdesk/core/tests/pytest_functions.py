from typing import AsyncGenerator, cast
import asyncio
import contextvars
import traceback
import functools
from pathlib import Path
from pytest import fixture

from quart import Quart
from quart.testing import QuartCliRunner

from superdesk.factory.app import SuperdeskApp

# from superdesk.core.tests import TestAppContext, TestAppFactory, TestSignals
from superdesk.core.tests import TestAppContext
from superdesk.core.tests.app import TestAppFactory

from .http_client import TestClient
import logging


logger = logging.getLogger(__name__)
_context: contextvars.ContextVar[TestAppContext] = contextvars.ContextVar("context")


class PytestFunctionFactory(TestAppFactory):
    pass


def setup_pytest(context: TestAppContext, factory: TestAppFactory | None = None) -> None:
    context.factory = factory or TestAppFactory()
    context.factory.test_type = "pytest"
    _context.set(context)


# TODO-PR: Try and remove this, now that we're trying to run 1 event loop per session
class Task311(asyncio.tasks.Task):
    """
    This is backport of Task from CPython 3.11
    It's needed to allow context passing
    """

    def __init__(self, coro, *args, loop=None, name=None, context=None):
        super(asyncio.tasks.Task, self).__init__(loop=loop)

        if self._source_traceback:
            del self._source_traceback[-1]
        if not asyncio.coroutines.iscoroutine(coro):
            # raise after Future.__init__(), attrs are required for __del__
            # prevent logging for pending task in __del__
            self._log_destroy_pending = False
            raise TypeError(f"a coroutine was expected, got {coro!r}")

        if name is None:
            self._name = f"Task-{asyncio.tasks._task_name_counter()}"
        else:
            self._name = str(name)

        self._num_cancels_requested = 0
        self._must_cancel = False
        self._fut_waiter = None
        self._coro = coro
        if context is None:
            self._context = contextvars.copy_context()
        else:
            self._context = context

        self._loop.call_soon(self._Task__step, context=self._context)
        asyncio.tasks._register_task(self)


class CustomEventLoopPolicy(asyncio.DefaultEventLoopPolicy):
    _testing: bool = False

    def set_event_loop(self, loop):
        if loop is not None:
            context = contextvars.copy_context()
            loop.set_task_factory(functools.partial(task_factory, context=context))
        super().set_event_loop(loop)


def task_factory(loop, coro, context=None):
    stack = traceback.extract_stack()
    for frame in stack[-2::-1]:
        package_name = Path(frame.filename).parts[-2]
        if package_name != "asyncio":
            if package_name == "pytest_asyncio":
                # This function was called from pytest_asyncio, use shared context
                break
            else:
                # This function was called from somewhere else, create context copy
                # break
                context = None
            break
    return Task311(coro, loop=loop, context=context)


@fixture(scope="session")
def event_loop_policy(request):
    print("event_loop_policy")
    _context.set(TestAppContext())
    return CustomEventLoopPolicy()


@fixture(scope="session", autouse=True)
def context() -> TestAppContext:
    return _context.get()


@fixture(scope="module", autouse=True)
async def app_module(context: TestAppContext) -> AsyncGenerator[None, None]:
    await context.factory.before_module(context)

    # if context.factory.signals.before_module:
    #     await context.factory.signals.before_module(context)
    yield
    await context.factory.after_module(context)
    # if context.factory.signals.after_module:
    #     await context.factory.signals.after_module(context)


@fixture(scope="function", autouse=True)
async def app_function(context: TestAppContext) -> AsyncGenerator[None, None]:
    await context.factory.before_test(context)
    # if context.factory.signals.before_test:
    #     await context.factory.signals.before_test(context)
    yield
    await context.factory.after_test(context)
    # if context.factory.signals.after_test:
    #     await context.factory.signals.after_test(context)


@fixture
async def app(context: TestAppContext) -> AsyncGenerator[SuperdeskApp, None]:
    yield context.app


#
# @fixture
# async def app(context: TestAppContext) -> AsyncGenerator[SuperdeskApp, None]:
#     if context.factory.signals.before_test:
#         await context.factory.signals.before_test(context)
#
#     # context.app_context = context.app.app_context()
#     # await context.app_context.push()
#     # async with context.app.app_context():
#     yield context.app
#     # await app_context.pop()
#     # async with context.app.app_context():
#     #     yield context.app
#
#     if context.factory.signals.after_test:
#         await context.factory.signals.after_test(context)
#
#
@fixture
def client(app: Quart) -> TestClient:
    return cast(TestClient, app.test_client())


@fixture
def runner(app: Quart) -> QuartCliRunner:
    """Necessary fixture to invoke click commands from unit tests"""
    return app.test_cli_runner()
