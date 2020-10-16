# flake8: noqa D403

"""
.. module:: expect
   :synopsis: Expectations

Expectation helper functions are receiving response object
(for example from `requests <http://docs.python-requests.org/>`_ lib)
as first argument.
These helpers make testing API response bodies and headers easy with minimal
time and effort.

.. moduleauthor:: Yauhen Kirylau <actionless.loveless@gmail.com>

"""


from .assertions import (
    assert_equal, assert_not_equal,
    assert_in, assert_not_in)
from .general import (
    parse_json_input, parse_json_response, apply_path, get_body,
    assert_and_print_body, WooperAssertionError, fail_and_print_body)


def expect_status(response, code):
    """
    checks if response status equals given code

    :param int code: Expected status code

    """
    assert_and_print_body(
        response,
        assert_equal,
        code, response.status_code,
        "Status code not matches.")


def expect_status_in(response, codes):
    """
    checks if response status equals to one of the provided

    :param list codes: List of valid status codes

    """
    assert_and_print_body(
        response,
        assert_in,
        response.status_code, codes,
        "Status code not matches.")


def expect_json(response, expected_json, path=None):
    """
    checks if json response equals some json,

    :param expected_json: JSON object to compare with
    :type expected_json: str, list, dict

    :param path: Path inside response json,
        separated by slashes, ie 'foo/bar/spam', 'foo/[0]/bar'
    :type path: str, optional

    """
    expected_json = parse_json_input(expected_json)
    json_response = apply_path(parse_json_response(response), path)
    assert_equal(expected_json, json_response, "JSON not matches")


def expect_json_match(response, expected_json, path=None):
    """
    checks if json response partly matches some json,

    :param expected_json: JSON object to compare with
    :type expected_json: str, list, dict

    :param path: Path inside response json,
        separated by slashes, ie 'foo/bar/spam', 'foo/[0]/bar'
    :type path: str, optional

    """
    def _json_match(response_data, expected_data, message):
        if isinstance(response_data, dict):
            for key in expected_data:
                assert_in(key, response_data)
                _json_match(response_data[key], expected_data[key], message)
        elif isinstance(response_data, list):
            for expected_item in expected_data:
                found = False
                for response_item in response_data:
                    try:
                        _json_match(response_item, expected_item, message)
                    except WooperAssertionError:
                        pass
                    else:
                        found = True
                        break
                assert_equal(found, True)
        else:
            assert_equal(expected_data, response_data)

    expected_json = parse_json_input(expected_json)
    json_response = apply_path(parse_json_response(response), path)
    try:
        _json_match(json_response, expected_json, "")
    except WooperAssertionError:
        fail_and_print_body(response, "JSON not matches")


def expect_json_contains(response, expected_json, path=None,
                         reverse_expectation=False):
    """
    checks if json response contains some json subset,

    :param expected_json: JSON object to compare with
    :type expected_json: str, list, dict

    :param path: Path inside response json,
        separated by slashes, ie 'foo/bar/spam', 'foo/[0]/bar'
    :type path: str, optional

    """

    assert_item = assert_equal
    assert_sequence = assert_in
    key_message = "JSON response does not contain such key"
    value_message = "JSON response does not contain such value"
    if reverse_expectation:
        assert_item = assert_not_equal
        assert_sequence = assert_not_in
        key_message = "JSON response contains such key"
        value_message = "JSON response contains such value"

    expected_json = parse_json_input(expected_json)
    json_response = apply_path(parse_json_response(response), path)

    if isinstance(expected_json, dict) and isinstance(json_response, dict):
        for key in expected_json.keys():
            if not reverse_expectation:
                assert_and_print_body(
                    response,
                    assert_sequence,
                    key,
                    json_response,
                    key_message)
            assert_and_print_body(
                response,
                assert_item,
                expected_json[key],
                json_response[key],
                value_message)
    else:
        assert_and_print_body(
            response,
            assert_sequence,
            expected_json, json_response,
            value_message)


def expect_json_not_contains(response, expected_json, path=None):
    """
    checks if json response not contains some json subset,

    :param expected_json: JSON object to compare with
    :type expected_json: str, list, dict

    :param path: Path inside response json,
        separated by slashes, ie 'foo/bar/spam', 'foo/[0]/bar'
    :type path: str, optional

    """
    return expect_json_contains(response, expected_json, path,
                                reverse_expectation=True)


def expect_headers_contain(response, header, value=None):
    """
    checks if response headers contain a given header

    :param str header: Expected header name.

    :param value: Expected header value.
    :type value: str, optional

    """
    assert_in(header,
              response.headers,
              "No such header in response.")
    if value:
        assert_equal(value,
                     response.headers[header],
                     "Header value not matches.")


def expect_headers(response, headers, partly=False):
    """
    checks if response headers values are equal to given

    :param dict headers: Dict with headers and their values,
        like { "Header1": "ExpectedValue1" }

    :param partly: Compare full header value or
        check if the value includes expected one.
    :type partly: bool, optional

    """
    for header, value in headers.items():
        expect_headers_contain(response, header)
        if partly:
            assert_in(value.lower(),
                      response.headers[header].lower(),
                      "Header not matches.")
        else:
            assert_equal(value.lower(),
                         response.headers[header].lower(),
                         "Header not matches.")


def expect_json_length(response, length, path=None):
    """
    checks if count of objects in json response equals provided length,

    :param int length: Expected number of objects inside json
        or length of the string

    :param path: Path inside response json,
        separated by slashes, ie 'foo/bar/spam', 'foo/[0]/bar'
    :type path: str, optional

    """
    json_response = apply_path(parse_json_response(response), path)
    assert_in(type(json_response), (list, dict),
              "'{}' isn't json.".format(json_response))
    assert_equal(length, len(json_response),
                 "JSON objects count not matches.")


def expect_body_contains(response, text):
    """
    checks if response body contains some text

    :param str text: Expected text
    """
    assert_in(text, get_body(response), "Body not contains '{}'.".format(text))
