import pytest

from superdesk.tests.steps import json_match


def test_empty_list_matches_empty_response():
    assert json_match([], [])


def test_empty_list_does_not_match_non_empty_response():
    assert not json_match([], [{"key": "value"}])


def test_non_empty_list_matches_superset_response():
    assert json_match([{"key": "value"}], [{"key": "value"}, {"key": "other"}])


def test_non_empty_list_does_not_match_missing_item():
    assert not json_match([{"key": "missing"}], [{"key": "value"}])
