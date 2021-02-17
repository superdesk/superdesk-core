from nose.plugins.attrib import attr


def wip(f):
    """Allows to run a single test using a @wip decorator

    i.e.
    from superdesk.tests import TestCase
    from tests import wip


    class TestWIP(TestCase):
        @wip
        def test_something(self):
            self.assertEqual(1, 1)

    then run with:
    nosetests -a wip
    """

    return attr("wip")(f)
