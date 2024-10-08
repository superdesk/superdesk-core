import pathlib
from typing import Literal


FixtureFolder = Literal["io", "media"]


def fixture_path(filename: str, folder: FixtureFolder) -> pathlib.Path:
    """Returns the full path to a fixture file"""
    return pathlib.Path(__file__).parent.joinpath(folder, "fixtures", filename)
