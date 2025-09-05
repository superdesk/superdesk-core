from typing import Callable, Any
from functools import partial
from os import environ
import asyncio
import logging

from behave.runner import Context as BaseContext, ModelRunner

from .common import TestAppContext
from .app import setup_mock_notifications, TestAppFactory


logger = logging.getLogger(__name__)


def run_async_task(task):
    """
    Runs async task until completes and logs any exceptions.
    """
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(task)
    except Exception as e:
        logger.exception(e)
        raise e


class BehaveTestFactory(TestAppFactory):
    test_type = "behave"

    async def before_test(self, context: "BehaveContext") -> bool:
        await super().before_test(context)

        if "skip" in context.scenario.tags:
            context.scenario.skip("Marked with @skip")
            return False
        if context.scenario.status == "skipped":
            return False

        context.headers = [("Content-Type", "application/json"), ("Origin", "localhost")]

        if "notification" in context.scenario.tags:
            setup_mock_notifications(context)

        return True


class BehaveContext(BaseContext, TestAppContext):
    factory: BehaveTestFactory


SIGNAL_TO_BEHAVE_HOOK: dict[str, str] = {
    "after_all": "after_all",
    "before_module": "before_feature",
    "after_module": "after_feature",
    "before_test": "before_scenario",
    "after_test": "after_scenario",
    "before_step": "before_step",
    "after_step": "after_step",
}


def setup_behave(context: BehaveContext, factory: BehaveTestFactory | None = None) -> None:
    environ["BEHAVE_TESTING"] = "1"

    context.factory = factory or BehaveTestFactory()
    _setup_behave_hooks_to_context_signals(context)


def _setup_behave_hooks_to_context_signals(context: BehaveContext) -> None:
    runner: ModelRunner | None = getattr(context, "_runner", None)
    if not runner:
        raise Exception("context runner not available")

    def hook_func(handler: Callable[[BehaveContext], None], current_context: BehaveContext, *args, **kwargs) -> None:
        run_async_task(handler(current_context))

    for signal_name, hook_name in SIGNAL_TO_BEHAVE_HOOK.items():
        signal = getattr(context.factory, signal_name, None)
        if signal:
            runner.hooks[hook_name] = partial(hook_func, signal)


def set_placeholder(context: BehaveContext, name: str, value: Any) -> None:
    old_p = getattr(context, "placeholders", None)
    if not old_p:
        context.placeholders = dict()
    context.placeholders[name] = value
