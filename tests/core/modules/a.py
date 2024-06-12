from superdesk.core.module import Module, SuperdeskAsyncApp


def init(app: SuperdeskAsyncApp):
    pass


module = Module(name="tests.module_a", init=init)
