from unittest import IsolatedAsyncioTestCase
from unittest.mock import Mock, AsyncMock
from superdesk.core import AsyncSignal


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
