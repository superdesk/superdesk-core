from pprint import pprint
import json
import os

from requests import Session

from .general import parse_json_response, apply_path


def get_url(context, uri):
    return context.server_url + uri


def request(context, method, uri, data=None, *args,
            add_server=True, **kwargs):

    if isinstance(data, dict) or isinstance(data, list):
        data = json.dumps(data)

    if not context.session:
        context.session = Session()

    if add_server:
        url = get_url(context, uri)
    else:
        url = uri

    if 'headers' in kwargs:
        headers = kwargs.pop('headers')
    else:
        headers = {}

    if context.print_url:
        print('{method} {url}'.format(method=method, url=url))
    if context.print_payload and 'data' in kwargs:
        print(kwargs['data'])

    if context.print_headers:
        pprint(headers)

    context.response = context.session.request(
        method,
        url,
        *args,
        data=data,
        headers=headers,
        verify=context.template_variables.get(
            'enable_ssl_verification', False
        ),
        **kwargs
    )


def GET(context, uri, *args, **kwargs):
    request(context, 'GET', uri, *args, **kwargs)


def POST(context, uri, *args, **kwargs):
    request(context, 'POST', uri, *args, **kwargs)


def PATCH(context, uri, *args, **kwargs):
    request(context, 'PATCH', uri, *args, **kwargs)


def PUT(context, uri, *args, **kwargs):
    request(context, 'PUT', uri, *args, **kwargs)


def DELETE(context, uri, *args, **kwargs):
    request(context, 'DELETE', uri, *args, **kwargs)


def json_response(context):
    json_dict = parse_json_response(context.response)
    return json_dict


def get_id_from_href(context, path=None):
    input_json = apply_path(json_response(context), path)
    item_id = os.path.basename(input_json['href'])
    return int(item_id)
