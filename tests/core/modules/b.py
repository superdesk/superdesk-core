from superdesk.core.module import Module, SuperdeskAsyncApp


def init(app: SuperdeskAsyncApp):
    pass


module = Module(name="tests.module_b", init=init, frozen=True, priority=1)
