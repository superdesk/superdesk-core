import pathlib
from typing import Literal

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


FixtureFolder = Literal["io", "media"]


def fixture_path(filename: str, folder: FixtureFolder) -> pathlib.Path:
    """Returns the full path to a fixture file"""
    return pathlib.Path(__file__).parent.joinpath(folder, "fixtures", filename)
