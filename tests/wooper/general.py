import json
from pprint import pformat


class WooperAssertionError(AssertionError):
    pass


def _format_message_text_and_body(response, message):
    body = getattr(response, 'text', None)
    if not body:
        try:
            body = response.data.decode("utf-8")
        except UnicodeDecodeError:
            body = response.data
        except Exception:
            body = '%%%_not_text_%%%'
    return (
        "{message}\n"
        "Response body:"
        '"""'
        "{body}"
        '"""'
        .format(message=message, body=body))


def assert_and_print_body(response, assert_function, first, second, message):
    return assert_function(
        first, second, _format_message_text_and_body(response, message)
    )


def fail(msg=None):
    """Fail immediately, with the given message."""
    raise WooperAssertionError(msg)


def fail_and_print_body(response, message):
    fail(_format_message_text_and_body(response, message))


def apply_path(json_dict, path):
    if not path:
        return json_dict
    path_elements = path.split('/')
    for element in path_elements:
        if element.startswith('['):
            try:
                element = int(element.lstrip('[').rstrip(']'))
            except ValueError as e:
                fail("Path can't be applied: {exception}."
                     .format(exception=e.args))
        try:
            json_dict = json_dict[element]
        except (IndexError, TypeError, KeyError):
            fail(
                "Path can't be applied:"
                "no such index '{index}' in " '"""{dict}""".'
                .format(index=element, dict=pformat(json_dict)))
    return json_dict


def parse_json_input(json_dict):
    if isinstance(json_dict, str) \
       and ('{' in json_dict or '[' in json_dict):
        try:
            return json.loads(json_dict)
        except ValueError:
            fail('You have provided not a valid JSON.')
    else:
        return json_dict


def get_body(response):
    body = getattr(response, 'text', None)
    if not body:
        try:
            body = response.data.decode("utf-8")
        except UnicodeDecodeError:
            body = response
        except Exception:
            fail("Response body is not text.")
    return body


def parse_json_response(response):
    try:
        return json.loads(get_body(response))
    except ValueError:
        fail_and_print_body(response, 'Response in not a valid JSON.')
