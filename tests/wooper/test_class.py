# flake8: noqa

"""
.. module:: test_class
   :synopsis: Testclass and mixing for using together with unittest

.. moduleauthor:: Yauhen Kirylau <actionless.loveless@gmail.com>

"""

import json
from pprint import pprint
from unittest import TestCase

from requests import Session

from .expect import (
    expect_status, expect_status_in,
    expect_json, expect_json_match, expect_json_contains,
    expect_headers, expect_headers_contain,
    expect_json_length, expect_body_contains,
)
from .general import apply_path, WooperAssertionError


class ApiMixin:
    """
    This class can be used as a mixin to `unittest.TestCase
    <https://docs.python.org/3.4/library/unittest.html#unittest.TestCase>`_
    to provide additional methods for requesting, inspecting and testing
    REST API services.
    """

    server_url = None
    """ Server URL """

    enable_ssl_verification = True
    """ Enable SSL certificates' verification (default: True) """

    print_url = False
    """ Print URLs during test run """

    print_payload = False
    """ Print payload sent to the server during test run """

    print_headers = False
    """ Print requests' headers during test run """

    maxDiff = None

    session = None

    response = None

    def _apply_path(self, json_dict, path):
        result = None
        try:
            result = apply_path(json_dict, path)
        except WooperAssertionError as e:
            self.fail("Path can't be applied: {exception}."
                      .format(exception=e.args))
        else:
            return result

    def get_url(self, uri):
        # get current base URL
        return self.server_url.rstrip('/') + uri

    def request(self, method, uri, *args,
                headers=None, add_server=True, **kwargs):
        if not self.session:
            self.session = Session()

        if add_server:
            url = self.get_url(uri)
        else:
            url = uri

        if self.print_url:
            print('{method} {url}'.format(method=method, url=url))
        if self.print_payload and 'data' in kwargs:
            pprint(kwargs['data'])
        if self.print_headers:
            pprint(headers)

        self.response = self.session.request(
            method, url, *args,
            verify=self.enable_ssl_verification, headers=headers, **kwargs
        )

    def request_with_data(self, method,  uri, *args, data='', **kwargs):
        if isinstance(data, dict) or isinstance(data, list):
            data = json.dumps(data)
        self.request(method, uri, *args, data=data, **kwargs)

    def GET(self, *args, **kwargs):
        """
        make a GET request to some URI

        :param str uri: URI

        rest of args is the same as in requests.get()
        """
        self.request('GET', *args, **kwargs)

    def POST(self, *args, **kwargs):
        """
        make a POST request to some URI

        :param str uri: URI
        :param data: request payload
        :type data: str, list, dict

        rest of args is the same as in requests.post()
        """
        self.request_with_data('POST', *args, **kwargs)

    def PATCH(self, *args, **kwargs):
        """
        make a PATCH request to some URI

        :param str uri: URI
        :param data: request payload
        :type data: str, list, dict

        rest of args is the same as in requests.patch()
        """
        self.request_with_data('PATCH', *args, **kwargs)

    def PUT(self, *args, **kwargs):
        """
        make a PUT request to some URI

        :param str uri: URI
        :param data: request payload
        :type data: str, list, dict

        rest of args is the same as in requests.put()
        """
        self.request_with_data('PUT', *args, **kwargs)

    def DELETE(self, *args, **kwargs):
        """
        make a DELETE request to some URI

        :param str uri: URI

        rest of args is the same as in requests.delete()
        """
        self.request('DELETE', *args, **kwargs)

    @property
    def json_response(self):
        """
        :returns: response as json
        :throws ValueError: if response is not a valid json
        """
        try:
            return json.loads(self.response.text)
        except ValueError:
            self.fail('Response in not a valid JSON.')

    def inspect_json(self, path=None):
        json_response = self._apply_path(self.json_response, path)
        pprint(json_response)

    def inspect_body(self):
        pprint(self.response.text)

    def inspect_status(self):
        print(self.response.status_code)

    def inspect_headers(self):
        pprint(dict(self.response.headers))

    def expect_status(self, code):
        """
        checks if response status equals given code

        :param int code: Expected status code

        """
        expect_status(self.response, code)

    def expect_status_in(self, codes):
        """
        checks if response status equals to one of the provided

        :param list codes: List of valid status codes

        """
        expect_status_in(self.response, codes)

    def expect_json(self, expected_json, path=None):
        """
        checks if json response equals some json,

        :param expected_json: JSON object to compare with
        :type expected_json: str, list, dict

        :param path: Path inside response json,
            separated by slashes, ie 'foo/bar/spam', 'foo/[0]/bar'
        :type path: str, optional

        """
        expect_json(self.response, expect_json, path)

    def expect_json_match(self, expected_json, path=None):
        """
        checks if json response partly matches some json,

        :param expected_json: JSON object to compare with
        :type expected_json: str, list, dict

        :param path: Path inside response json,
            separated by slashes, ie 'foo/bar/spam', 'foo/[0]/bar'
        :type path: str, optional

        """
        expect_json_match(self.response, expected_json, path)

    def expect_json_contains(self, expected_json, path=None,
                             reverse_expectation=False):
        """
        checks if json response contains some json subset,

        :param expected_json: JSON object to compare with
        :type expected_json: str, list, dict

        :param path: Path inside response json,
            separated by slashes, ie 'foo/bar/spam', 'foo/[0]/bar'
        :type path: str, optional

        """
        expect_json_contains(self.response, expected_json, path,
                             reverse_expectation)

    def expect_json_not_contains(self, expected_json, path=None):
        """
        checks if json response not contains some json subset,

        :param expected_json: JSON object to compare with
        :type expected_json: str, list, dict

        :param path: Path inside response json,
            separated by slashes, ie 'foo/bar/spam', 'foo/[0]/bar'
        :type path: str, optional

        """
        expect_json_contains(self.response, expected_json, path,
                             reverse_expectation=True)

    def expect_headers(self, headers, partly=False):
        """
        checks if response headers values are equal to given

        :param dict headers: Dict with headers and their values,
            like { "Header1": "ExpectedValue1" }

        :param partly: Compare full header value or
            check if the value includes expected one.
        :type partly: bool, optional

        """
        expect_headers(self.response, headers, partly)

    def expect_headers_contain(self, header, value=None):
        """
        checks if response headers contain a given header

        :param str header: Expected header name.

        :param value: Expected header value.
        :type value: str, optional

        """
        expect_headers_contain(self.response, header, value)

    def expect_json_length(self, length, path=None):
        """
        checks if count of objects in json response equals provided length,

        :param int length: Expected number of objects inside json
            or length of the string

        :param path: Path inside response json,
            separated by slashes, ie 'foo/bar/spam', 'foo/[0]/bar'
        :type path: str, optional

        """
        expect_json_length(self.response, length)

    def expect_body_contains(self, text):
        """
        checks if response body contains some text

        :param str text: Expected text
        """
        expect_body_contains(self.response, text)


class ApiTestCase(TestCase, ApiMixin):
    pass
