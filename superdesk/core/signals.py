from typing import Generic, Callable, Awaitable
from typing_extensions import TypeVarTuple, Unpack
from inspect import isawaitable


SignalFunctionSignature = TypeVarTuple("SignalFunctionSignature")


class AsyncSignal(Generic[Unpack[SignalFunctionSignature]]):
    """Strictly typed event signal system

    An event signalling system that is strictly typed.
    This means that we're able to run ``mypy`` to check the types connected to, or executing, signal callbacks,
    potentially raising type errors before they're able to get to an instance and cause a bug.

    You're able to define a signal with variable number of arguments, without an upper limit on the number of arguments.

    You create a signal by constructing an instance of one, providing the function signature types and name of the signal.

    AsyncSignal[``<function signature>``](``<signal name>``):

    * ``function signature``: A variable list of argument types
    * ``signal name``: The name of the signal

    The signal supports both sync and async listeners to be added to its listeners.

    Example signal::

        # file: users/signals.py
        from superdesk.core import AsyncSignal
        from .types import UserResourceModel

        before_user_created = AsyncSignal[UserResourceModel](
            "user:before_created"
        )
        on_user_created = AsyncSignal[UserResourceModel](
            "user:on_created"
        )

        async create_user(user: UserResourceModel):
            await before_user_created.send(user)
            await UserResourceModel.get_service().create([user])
            await on_user_created.send(user)

    Example connecting::

        # file: my/module.py
        from users import UserResourceModel, signals as user_signals

        async def before_user_created(user: UserResourceModel) -> None:
            # Do something before the user is created
            ...

        async def on_user_created(user: UserResourceModel) -> None:
            # Do something with the user that was just created
            ...

        async def invalid_signal_callback(arg1: bool) -> str:
            return "True" if arg1 else "False"

        def init_module():
            user_signals.before_user_created += before_user_created
            user_signals.on_user_created += on_user_created

            # This next line will cause ``mypy`` checks to fail
            # as the signature is invalid for the signal
            user_signals.on_user_created += invalid_signal_callback
    """

    #: Name of the signal
    name: str

    _listeners: set[Callable[[Unpack[SignalFunctionSignature]], Awaitable[None] | None]]

    def __init__(self, name: str):
        self.name = name
        self._listeners = set()

    def __repr__(self):
        return f"signal '{self.name}'"

    def connect(self, callback: Callable[[Unpack[SignalFunctionSignature]], Awaitable[None] | None]) -> None:
        """Connect a function to this signal, to be called when fired

        You can also use the inline add operator to connect to a signal.
        Example::

            signal.connect(cb)
            # is the same as
            signal += cb

        :param callback: function to register with this signal
        """

        self._listeners.add(callback)

    def disconnect(self, callback: Callable[[Unpack[SignalFunctionSignature]], Awaitable[None] | None]) -> None:
        """Remove a function from this signal

        You can also use the inline subtract operator to remove a callback from a signal.
        Example::

            signal.disconnect(cb)
            # is the same as
            signal -= cb

        :param callback: function to remove from this signal
        """

        self._listeners.remove(callback)

    def __iadd__(self, callback: Callable[[Unpack[SignalFunctionSignature]], Awaitable[None] | None]):
        """Connect a function to this signal, to be called when fired

        :param callback: function to register with this signal
        """

        self.connect(callback)

    def __isub__(self, callback: Callable[[Unpack[SignalFunctionSignature]], Awaitable[None] | None]):
        """Remove a function from this signal

        :param callback: function to remove from this signal
        """

        self.disconnect(callback)

    def __len__(self):
        return len(self._listeners)

    async def __call__(self, *args: Unpack[SignalFunctionSignature]) -> None:
        await self.send(*args)

    async def send(self, *args: Unpack[SignalFunctionSignature]) -> None:
        """Call all the registered callbacks connected to this signal

        You can also use the call operator to call registered callbacks.
        Example::

            signal.send(args)
            # is the same as
            signal(args)

        :param args: The arguments to send to each registered function
        """

        for callback in self._listeners:
            response = callback(*args)
            if isawaitable(response):
                await response
