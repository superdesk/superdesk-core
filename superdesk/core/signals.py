from typing import Generic, Callable, Awaitable, Iterable, ClassVar
from typing_extensions import TypeVarTuple, Unpack, Self
from inspect import isawaitable, iscoroutinefunction, getmembers, get_annotations


SignalFunctionSignature = TypeVarTuple("SignalFunctionSignature")
SignalListener = Callable[[Unpack[SignalFunctionSignature]], None]
AsyncSignalListener = Callable[[Unpack[SignalFunctionSignature]], Awaitable[None] | None] | SignalListener


class Signal(Generic[Unpack[SignalFunctionSignature]]):
    """
    A synchronous signal
    """

    #: Name of the signal
    _name: str

    _async = False
    _default_listeners: set[AsyncSignalListener]
    _listeners: set[AsyncSignalListener]

    def __init__(self, name: str, listeners: Iterable[AsyncSignalListener] | None = None):
        self._name = name
        self._default_listeners = set(listeners) if listeners else set()
        self._listeners = self._default_listeners.copy()

    def __repr__(self):
        return f"signal '{self.name}'"

    @property
    def name(self) -> str:
        return self._name

    def connect(self, callback: Callable[[Unpack[SignalFunctionSignature]], Awaitable[None] | None]) -> None:
        """Connect a function to this signal, to be called when fired

        You can also use the inline add operator to connect to a signal.
        Example::

            signal.connect(cb)
            # is the same as
            signal += cb

        :param callback: function to register with this signal
        """

        if not self._async and iscoroutinefunction(callback):
            raise RuntimeError(f"Async listener attempting to be added to sync signal: {self}")

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

    def clear_listeners(self) -> None:
        self._listeners = set()
        # self._listeners = self._default_listeners.copy()

    def __iadd__(self, callback: Callable[[Unpack[SignalFunctionSignature]], Awaitable[None] | None]):
        """Connect a function to this signal, to be called when fired

        :param callback: function to register with this signal
        """

        self.connect(callback)
        return self

    def __isub__(self, callback: Callable[[Unpack[SignalFunctionSignature]], Awaitable[None] | None]):
        """Remove a function from this signal

        :param callback: function to remove from this signal
        """

        self.disconnect(callback)
        return self

    def __len__(self):
        return len(self._listeners)

    def __call__(self, *args: Unpack[SignalFunctionSignature]) -> None:
        self.send(*args)

    def send(self, *args: Unpack[SignalFunctionSignature]) -> None:
        """Call all the registered callbacks connected to this signal

        You can also use the call operator to call registered callbacks.
        Example::

            signal.send(args)
            # is the same as
            signal(args)

        :param args: The arguments to send to each registered function
        """

        for callback in self._listeners:
            callback(*args)


class AsyncSignal(Signal[Unpack[SignalFunctionSignature]], Generic[Unpack[SignalFunctionSignature]]):
    """
    An asynchronous signal
    """

    _async = True

    async def __call__(self, *args: Unpack[SignalFunctionSignature]) -> None:  # type: ignore[override]
        await self.send(*args)

    async def send(self, *args: Unpack[SignalFunctionSignature]) -> None:  # type: ignore[override]
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


class SignalGroup:
    """
    A mixin for supporting class signal attributes

    * Fields that start with `on_` and have no value, will be auto-initialised
    * Util methods to:
        * get instance attributes that are Signal, AsyncSignal, or SignalGroup
        * clear all listeners
        * connect another group to common signals in this group
    """

    #: Optional prefix string used when auto-initialising class signal attributes
    signal_name_prefix: ClassVar[str] = ""

    def __init__(self):
        # Initialise all fields that are
        # * not already defined
        # * it's type is a sub-class of ``Signal``, ``AsyncSignal`` or ``SignalGroup``

        for field_name, annotation in get_annotations(self.__class__).items():
            if not field_name.startswith("on_") or getattr(self, field_name, None) is not None:
                continue

            try:
                annotation_instance = annotation()
            except TypeError:
                annotation_instance = annotation(f"{self.signal_name_prefix}{field_name}")

            if isinstance(annotation_instance, (Signal, AsyncSignal, SignalGroup)):
                setattr(self, field_name, annotation_instance)

    def __repr__(self):
        return f"signal group '{self.__class__.__name__}'"

    def get_all_signals(self) -> list[tuple[str, Signal | AsyncSignal]]:
        """Get all attributes of this class that are a ``Signal`` or ``AsyncSignal`` instance"""

        return getmembers(self, lambda x: isinstance(x, (Signal, AsyncSignal)))

    def get_all_groups(self) -> list[tuple[str, Self]]:
        """Get all attributes of this class that are an instance of ``SignalGroup``"""

        return getmembers(self, lambda x: isinstance(x, SignalGroup))

    def clear_listeners(self) -> None:
        """Clear all listeners for all group and signal attributes of this class"""

        for key, group in self.get_all_groups():
            group.clear_listeners()
        for key, signal in self.get_all_signals():
            signal.clear_listeners()

    def connect_group(self, group: Self):
        """Connect another group to common signals in this group"""

        for key, signal in self.get_all_signals():
            listener = getattr(group, key, None)
            if listener is not None:
                signal.connect(listener)
