.. core_signals:

======================
Signals / Event System
======================

.. module:: superdesk.core.signals

The signal mechanism provides a way to subscribe to events that can be raised by the system.

Signals are strictly typed,

Types Of Signals
----------------

At the core is the :class:`Signal` class, which provides the base functionality for all signal types.
There are also :class:`AsyncSignal` and :class:`SignalGroup` types, each with their own use cases.

Example definition and subscription of signals::

    from superdesk.core.signals import (
        Signal,
        AsyncSignal,
        SignalGroup
    )

    # Signal defined on a module level scope
    on_start = Signal[]("on_app_start")

    class MyClass(SignalGroup):
        # Signals defined on a class instance scope
        on_event: Signal[bool]
        on_event_async: AsyncSignal[str]

    # Define some callbacks
    def event_cb(arg1: bool):
        print(f"Value: {arg1}")

    async def event_cb_async(arg1: str):
        print(f"Value: {arg1}")

    async def main():
        # Example connecting, disconnecting and sending signals
        my_inst = MyClass()
        my_inst.on_event.connect(event_cb)
        my_inst.on_event_async.connect(event_cb_async)
        on_start.send()
        my_inst.on_event.send(True)
        await my_inst.on_event_async.send("Some Data")

Signal
******

Example signals::

    # Creating a module level signal
    on_create: Signal[dict]

    # Creating a class instance scoped signal
    class MyContext(SignalGroup):
        on_exit: Signal[bool]

There are two functions for subscribing to a signal:

* :meth:`connect() <Signal.connect>` - connect a function to this signal
* :meth:`disconnect() <Signal.disconnect>` - disconnect a function from this signal

When you :meth:`send() <Signal.send>` a signal, it runs all it's connected functions with the provided args.

Example::

    def on_create_cb(arg1: dict):
        pass

    def on_exit_cb(arg1: bool):
        pass

    def main():
        my_inst = MyContext()
        my_inst.on_exit.connect(on_exit_cb)

        on_create.connect(on_create_cb)
        on_create.send({"some": "data"})
        on_create.disconnect(on_create_cb)

        my_inst.on_exit.send(True)

.. autoclass:: superdesk.core.signals.Signal
    :member-order: bysource
    :members:



Async Signals
*************

Example signals::

    from superdesk.core.signals import AsyncSignal, SignalGroup

    # Creating a module level signal
    on_create: AsyncSignal[dict]

    # Creating a class instance scoped signal
    class MyContext(SignalGroup):
        on_exit: AsyncSignal[bool]

.. autoclass:: superdesk.core.signals.AsyncSignal
    :member-order: bysource
    :members:

Signal Groups
*************

As can be seen from the examples above, a SignalGroup is one way to easily scope signals to a class instance.
Any attribute on the class that starts with `on_` and has no value after ``__init__``, then a Signal, AsyncSignal or SignalGroup will be constructed for you.
This allows us to define the signals on the class without constructing them but by annotating them.

AsyncGroups can also be connected to another AsyncGroup::

    from superdesk.core.signals import Signal, SignalGroup

    class GroupA(SignalGroup):
        on_a1: Signal[bool]
        on_a2: Signal[str]

    class GroupB(SignalGroup):
        on_a: SignalGroup[GroupA])


.. autoclass:: superdesk.core.signals.SignalGroup
    :member-order: bysource
    :members:



Resource Signals
----------------

Resource signals are split up based on context, data or web.

Below is a short diagram showing when the resource signals are fired.
This example is when the API receives a request to create a new resource.

.. uml::

    title Create Resource Data Flow

    cloud "HTTP Request" as client
    cloud "HTTP Response" as client_response

    rectangle "Web: Process request" as web_process_request
    rectangle "Data: Process request" as data_process_request
    rectangle "Data: Process response" as data_process_response
    rectangle "Web: Process response" as web_process_response

    queue "web.on_create" as signal_web_create
    queue "web.on_created" as signal_web_created
    queue "data.on_create" as signal_data_create
    queue "data.on_created" as signal_data_created

    database "Mongo/Elastic" as db

    client --> web_process_request: Send create request
    web_process_request -> signal_web_create: Send signal
    web_process_request --> data_process_request: Send to data layer
    data_process_request -> signal_data_create: Send signal
    data_process_request --> db: Save data
    db --> data_process_response: New item
    data_process_response -> signal_data_created: Send signal
    data_process_response --> web_process_response: Send new item
    web_process_response -> signal_web_created: Send signal
    web_process_response --> client_response: Send response

.. autoclass:: superdesk.core.resources.resource_signals.ResourceSignals
    :member-order:
    :members:


Data Signals
************

The ResourceDataSignals class is used for signals around sending data to the DB.
Signals are sent before and after the following DB actions:

Example::

    from tests.core.modules.users import User

    def on_user_create(user: User) -> None:
        user.code = "test_user_code"

    def init_app():
        User.get_signals().data.on_create.connect(on_user_create)

Below are the available resource data signals, along with their types.

.. autoclass:: superdesk.core.resources.resource_signals.ResourceDataSignals
    :member-order: bysource
    :members:
    :exclude-members: signal_name_prefix

Web Signals
***********

The ResourceWebSignals class is used for signals around receiving API requests regarding resources.

Signals are sent before and after the following request actions:

Example::

    from superdesk.core.types import Request, Response
    from tests.core.modules.users import User

    def on_user_create(request: Request, users: list[User]) -> None:
        # Use the request object to apply some logic
        if not request.get_url_arg("add_code"):
            return

        # Update the resource data before it's saved in the DB
        for user in users:
            user.code = "test_user_code"

    def on_user_create_response(
        request: Request,
        response: Response
    ) -> None:
        # Add some headers to the response
        response.headers += (("X-Custom-Attribute", "SomeValidData"))

    def init_app():
        # Connect our resource listeners to the resource web signals
        signals = User.get_signals().web
        signals.on_create.connect(on_user_create)
        signals.on_create_response.connect(on_user_create_response)

Below are the available resource web signals, along with their types.

.. autoclass:: superdesk.core.resources.resource_signals.ResourceWebSignals
    :member-order: bysource
    :members:
    :exclude-members: signal_name_prefix

Global Resource Signals
-----------------------

Global resource signals exist so if you can hook code into signal(s) from all resources.
It is an instance of :class:`ResourceSignals <superdesk.core.resources.resource_signals.ResourceSignals>`.

You use it by importing the module level signal from superdesk.core.resources.global_signals.::

    from superdesk.core.resources import (
        ResourceModel,
        global_signals,
    )

    async def on_resource_created(doc: ResourceModel) -> None:
        print(f"{doc.type} - {doc.id}: created")

    global_signals.data.on_create.connect(on_resource_created)


Global Functions
----------------

.. autofunction:: superdesk.core.resources.resource_signals.get_resource_signals

.. autofunction:: superdesk.core.resources.resource_signals.clear_all_resource_signal_listeners

Example Signals
---------------

On Resource Registered
**********************

Example signal definition and subscription

Originally when registering a resource, the Resources module will be in charge of registering that resource with Mongo & Elastic.
This was hard coded::

    class Resources:
        ...

        def register(self, config: ResourceConfig):
            ...
            mongo_config = config.mongo or MongoResourceConfig()
            if config.versioning:
                mongo_config.versioning = True

            self.app.mongo.register_resource_config(
                config.name, mongo_config
            )
            ...

With the help of SignalGroups, modules no longer need to add their code to the Resources module,
but instead connect to the :meth:`on_resource_registered <superdesk.core.resources.resource_manager.Resources.on_resource_registered>` signal and add the registration code there. ::

    from superdesk.core.signals import Signal, SignalGroup

    class Resources(SignalGroup):
        on_resource_registered: Signal[
            SuperdeskAsyncApp,
            ResourceConfig
        ]

    def register(self, config: ResourceConfig):
            ...
            self.on_resource_registered.send(self.app, config)
            ...

And then in a mongo module::

    from superdesk.core.types import MongoResourceConfig
    from superdesk.core.app import SuperdeskAsyncApp
    from superdesk.core.resources import ResourceConfig

    def on_resource_registered(
        app: SuperdeskAsyncApp,
        config: ResourceConfig
    ) -> None:
        mongo_config = config.mongo or MongoResourceConfig()
        if config.versioning:
            mongo_config.versioning = True

        app.mongo.register_resource_config(config.name, mongo_config)

This way the Resources class does not need to know how to register resources for other modules.
