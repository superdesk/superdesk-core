import asyncio

from unittest import IsolatedAsyncioTestCase as AsyncTestCase


def get_loop():
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()

    asyncio.set_event_loop(loop)
    loop.set_debug(True)

    return loop


def call_async(func, /, *args, **kwargs):
    loop = get_loop()
    ret = func(*args, **kwargs)
    return loop.run_until_complete(ret)


class IsolatedAsyncioTestCase(AsyncTestCase):
    @classmethod
    def setUpClass(cls):
        """Hook method for setting up class fixture before running tests in the class."""
        call_async(cls.asyncSetUpClass)

    @classmethod
    def tearDownClass(cls):
        """Hook method for deconstructing the class fixture after running all tests in the class."""
        call_async(cls.asyncTearDownClass)

    @classmethod
    async def asyncSetUpClass(cls):
        """Hook method for setting up class fixture before running tests in the class."""
        pass

    @classmethod
    async def asyncTearDownClass(cls):
        """Hook method for setting up class fixture before running tests in the class."""
        pass

    def _setupAsyncioLoop(self):
        loop = get_loop()
        self._asyncioTestLoop = loop
        fut = loop.create_future()
        self._asyncioCallsTask = loop.create_task(self._asyncioLoopRunner(fut))
        loop.run_until_complete(fut)

    def _tearDownAsyncioLoop(self):
        assert self._asyncioTestLoop is not None, "asyncio test loop is not initialized"
        loop = self._asyncioTestLoop
        self._asyncioTestLoop = None
        self._asyncioCallsQueue.put_nowait(None)
        loop.run_until_complete(self._asyncioCallsQueue.join())

        # cancel all tasks
        to_cancel = asyncio.all_tasks(loop)
        if not to_cancel:
            return

        for task in to_cancel:
            task.cancel()

        loop.run_until_complete(asyncio.gather(*to_cancel, return_exceptions=True))

        for task in to_cancel:
            if task.cancelled():
                continue
            if task.exception() is not None:
                loop.call_exception_handler(
                    {
                        "message": "unhandled exception during test shutdown",
                        "exception": task.exception(),
                        "task": task,
                    }
                )
        # shutdown asyncgens
        loop.run_until_complete(loop.shutdown_asyncgens())

    # Python v3.12 changes
    def _tearDownAsyncioRunner(self):
        pass

    def _setupAsyncioRunner(self):
        assert self._asyncioRunner is None, "asyncio runner is already initialized"
        runner = asyncio.Runner(debug=True, loop_factory=get_loop)
        self._asyncioRunner = runner
