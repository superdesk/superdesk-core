import pytest

from superdesk.tests.steps import encode_url_query, json_match


def test_empty_list_matches_empty_response():
    assert json_match([], [])


def test_empty_list_does_not_match_non_empty_response():
    assert not json_match([], [{"key": "value"}])


def test_non_empty_list_matches_superset_response():
    assert json_match([{"key": "value"}], [{"key": "value"}, {"key": "other"}])


def test_non_empty_list_does_not_match_missing_item():
    assert not json_match([{"key": "missing"}], [{"key": "value"}])


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("/search?q=café", "/search?q=caf%C3%A9"),
        (
            '/search?where={"headline": "caf\\u00e9"}',
            "/search?where=%7B%22headline%22:%20%22caf%C3%A9%22%7D",
        ),
        ("/search?q=foo\\tbar", "/search?q=foo%09bar"),
        ("/search?q=foo\\rbar", "/search?q=foo%0Dbar"),
        ("/search?q=foo\\nbar", "/search?q=foo%0Abar"),
    ],
)
def test_encode_url_query(url, expected):
    assert encode_url_query(url) == expected
