# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


import os
import time
import arrow
import celery
import shutil
import responses
import operator

from unittest import mock
from copy import deepcopy
from base64 import b64encode
from datetime import datetime, timedelta, date
from os.path import basename
from re import findall
from unittest.mock import patch
from urllib.parse import urlparse
from pathlib import Path

from behave import given, when, then  # @UnresolvedImport
from bson import ObjectId
from eve.io.mongo import MongoJSONEncoder
from eve.methods.common import parse
from eve.utils import ParsedRequest, config
from flask import json, render_template_string
from wooper.assertions import assert_in, assert_equal, assertions
from wooper.general import fail_and_print_body, apply_path, parse_json_response, WooperAssertionError
from wooper.expect import (
    expect_status_in,
    expect_json,
    expect_json_length,
    expect_json_contains,
    expect_json_not_contains,
    expect_headers_contain,
)

import superdesk
from superdesk import tests
from superdesk import get_resource_service, utc, etree
from superdesk.io import get_feeding_service
from superdesk.io.commands import update_ingest
from superdesk.io.commands.update_ingest import LAST_ITEM_UPDATE
from superdesk.io.feeding_services import ftp
from superdesk.io.feed_parsers import XMLFeedParser, EMailRFC822FeedParser, STTNewsMLFeedParser
from superdesk.media.image import read_metadata
from superdesk.utc import utcnow, get_expiry_date
from superdesk.tests import get_prefixed_url, set_placeholder
from apps.dictionaries.resource import DICTIONARY_FILE
from superdesk.filemeta import get_filemeta
from apps.preferences import enhance_document_with_default_prefs
from apps.prepopulate.app_initialize import AppInitializeWithDataCommand

# for auth server
from authlib.jose import jwt
from authlib.jose.errors import BadSignatureError

external_url = "http://thumbs.dreamstime.com/z/digital-nature-10485007.jpg"
DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S%z"
ANALYTICS_DATETIME_FORMAT = "%Y-%m-%d %H:00:00"
# we need to set this variable to test auth server without HTTPS
os.environ["AUTHLIB_INSECURE_TRANSPORT"] = "1"


def expect_status(response, code):
    assert int(code) == response.status_code, "exptected {expected}, got {code}, reason={reason}".format(
        code=response.status_code,
        expected=code,
        reason=response.get_data().decode("utf-8"),
    )


def test_json(context, json_fields=None):
    if json_fields is None:
        json_fields = []
    try:
        response_data = json.loads(context.response.get_data())
    except Exception:
        fail_and_print_body(context.response, "response is not valid json")
    context_data = json.loads(apply_placeholders(context, context.text))
    assert json_match(context_data, response_data, json_fields), str(context_data) + "\n != \n" + str(response_data)
    return response_data


def test_json_with_string_field_value(context, field):
    try:
        response_data = json.loads(context.response.get_data())
    except Exception:
        fail_and_print_body(context.response, "response is not valid json")
    context_data = json.loads(apply_placeholders(context, context.text))

    assert_equal(
        json_match(context_data[field], response_data[field]),
        True,
        msg=str(context_data) + "\n != \n" + str(response_data),
    )
    return response_data


def test_key_is_present(key, context, response):
    """Test if given key is present in response.

    In case the context value is empty - "", {}, [] - it checks if it's non empty in response.

    If it's set in context to false, it will check that it's falsy/empty in response too.

    :param key
    :param context
    :param response
    """
    assert (
        not isinstance(context[key], bool) or not response[key]
    ), '"%s" should be empty or false, but it was "%s" in (%s)' % (key, response[key], response)


def test_key_is_not_present(key, response):
    """Test if given key is not present in response.

    :param key
    :param response
    """
    assert key not in response, '"%s" should not be present, but it was "%s" in (%s)' % (key, response[key], response)


def assert_is_now(val, key):
    """Assert that given datetime value is now (with 2s tolerance).

    :param val: datetime
    :param key: val label - used for error reporting
    """
    now = arrow.get()
    val = arrow.get(val)
    assert val + timedelta(seconds=2) > now, "%s should be %s, it is %s" % (key, now, val)


def json_match(context_data, response_data, json_fields=None, parent=None):
    if json_fields is None:
        json_fields = []
    if isinstance(context_data, dict):
        if not isinstance(response_data, dict):
            return False
        for key in context_data:
            if context_data[key] == "__none__":
                assert response_data.get(key) is None, "{} is not None ({})".format(key, response_data[key])
                continue
            if context_data[key] == "__no_value__":
                test_key_is_not_present(key, response_data)
                continue
            if key not in response_data:
                print(key, " not in ", response_data)
                return False
            if context_data[key] == "__any_value__":
                test_key_is_present(key, context_data, response_data)
                continue
            if context_data[key] == "__now__":
                assert_is_now(response_data[key], key)
                continue
            if context_data[key] == "__today__":
                assert response_data[key] == date.today().isoformat(), "{date} should be today ({today})".format(
                    date=response_data[key],
                    today=date.today().isoformat(),
                )
                continue
            if context_data[key] == "__future__":
                assert arrow.get(response_data[key]) > arrow.get(), "{} should be in future".format(key)
                continue
            if context_data[key] == "__empty__":
                assert len(response_data[key]) == 0, "%s is not empty (%s)" % (key, response_data[key])
                continue
            if context_data[key] == "__objectid__":
                assert ObjectId(response_data[key]), "{key} is not ObjectId ({value})".format(
                    key=key, value=response_data[key]
                )
                continue
            response_field = response_data[key]
            if key in json_fields:
                try:
                    response_field = json.loads(response_data[key])
                except Exception:
                    fail_and_print_body(response_data, "response does not contain a valid %s field" % key)
            if not json_match(context_data[key], response_field, json_fields, parent=key):
                print("key {} does not match in {}".format(key, parent or context_data))
                return False
        return True
    elif isinstance(context_data, list):
        for item_context in context_data:
            found = False
            for item_response in response_data:
                if json_match(item_context, item_response, json_fields):
                    found = True
                    break
            if not found:
                print(item_context, " not in ", json.dumps(response_data, indent=2))
                return False
        return True
    elif not isinstance(context_data, dict):
        if context_data != response_data:
            print("---" + str(context_data) + "---\n", " != \n", "---" + str(response_data) + "---\n")
        return context_data == response_data


def get_fixture_path(context, fixture):
    path = context.app.settings["BEHAVE_TESTS_FIXTURES_PATH"]
    return os.path.join(path, fixture)


def get_macro_path(macro):
    abspath = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    return os.path.join(abspath, "macros", macro)


def get_self_href(resource, context):
    assert "_links" in resource, 'expected "_links", but got only %s' % (resource)
    return resource["_links"]["self"]["href"]


def get_res(url, context):
    response = context.client.get(get_prefixed_url(context.app, url), headers=context.headers)
    expect_status(response, 200)
    return json.loads(response.get_data())


def parse_date(datestr):
    return datetime.strptime(datestr, DATETIME_FORMAT)


def format_date(date_to_format):
    return date_to_format.strftime(DATETIME_FORMAT)


def format_date_analytics(date_to_format):
    return date_to_format.strftime(ANALYTICS_DATETIME_FORMAT)


def assert_200(response):
    """Assert we get status code 200."""
    expect_status_in(response, (200, 201, 204))


def assert_404(response):
    """Assert we get status code 404."""
    assert response.status_code == 404, "Expected 404, got %d" % (response.status_code)


def assert_ok(response):
    """Assert we get ok status within api response."""
    expect_status_in(response, (200, 201))
    expect_json_contains(response, {"_status": "OK"})


def get_json_data(response):
    return json.loads(response.get_data())


def get_it(context):
    it = context.data[0]
    res = get_res("/%s/%s" % (context.resource, it["_id"]), context)
    return get_self_href(res, context), res.get("_etag")


def get_response_readable(data):
    try:
        return json.dumps(json.loads(data), indent=2)
    except (ValueError, TypeError):
        pass
    try:
        return data.decode("utf-8")
    except ValueError:
        pass
    return data


def if_match(context, etag):
    headers = []
    if etag:
        headers = [("If-Match", etag)]
    headers = unique_headers(headers, context.headers)
    return headers


def unique_headers(headers_to_add, old_headers):
    headers = dict(old_headers)
    for item in headers_to_add:
        headers.update({item[0]: item[1]})
    unique_headers = [(k, v) for k, v in headers.items()]
    return unique_headers


def patch_current_user(context, data):
    response = context.client.get(
        get_prefixed_url(context.app, "/users/%s" % context.user["_id"]), headers=context.headers
    )
    user = json.loads(response.get_data())
    headers = if_match(context, user.get("_etag"))
    response = context.client.patch(
        get_prefixed_url(context.app, "/users/%s" % context.user["_id"]), data=data, headers=headers
    )
    assert_ok(response)
    return response


def apply_placeholders(context, text):
    placeholders = getattr(context, "placeholders", {})
    for placeholder in findall('#([^#"]+)#', text):
        if placeholder.startswith("DATE"):
            value = utcnow()
            unit = placeholder.find("+")
            if unit != -1:
                value += timedelta(days=int(placeholder[unit + 1]))
            else:
                unit = placeholder.find("-")
                if unit != -1:
                    value -= timedelta(days=int(placeholder[unit + 1]))

            if placeholder == "ANALYTICS_DATE_FORMATTED":
                value = format_date_analytics(value)
            else:
                value = format_date(value)
            placeholders["LAST_DATE_VALUE"] = value
        elif placeholder not in placeholders:
            try:
                resource_name, field_name = placeholder.split(".", maxsplit=1)
            except Exception:
                continue
            resource = getattr(context, resource_name, None)
            for name in field_name.split("."):
                if not resource:
                    break

                resource = resource.get(name, None)

            if not resource:
                continue

            if isinstance(resource, datetime):
                value = format_date(resource)
            else:
                value = str(resource)
        else:
            value = placeholders[placeholder]
        text = text.replace("#%s#" % placeholder, value)
    return text


def get_resource_name(url):
    parsed_url = urlparse(url)
    return basename(parsed_url.path)


def format_items(items):
    output = [""]  # insert empty line
    for item in items:
        if item.get("formatted_item"):
            try:
                item["formatted_item"] = json.loads(item["formatted_item"])
            except ValueError:
                pass
        output.append(json.dumps(item, indent=4, sort_keys=True))
    return ",\n".join(output)


@given('empty "{resource}"')
def step_impl_given_empty(context, resource):
    if not is_user_resource(resource):
        with context.app.test_request_context(context.app.config["URL_PREFIX"]):
            get_resource_service(resource).delete_action()


@given('"{resource}"')
def step_impl_given_(context, resource):
    data = apply_placeholders(context, context.text)
    with context.app.test_request_context(context.app.config["URL_PREFIX"]):
        if not is_user_resource(resource):
            get_resource_service(resource).delete_action()

        items = [parse(item, resource) for item in json.loads(data)]
        if is_user_resource(resource):
            for item in items:
                item.setdefault("needs_activation", False)

        get_resource_service(resource).post(items)
        context.data = items
        context.resource = resource
        try:
            setattr(context, resource, items[-1])
        except KeyError:
            pass


@given('"{resource}" with objectid')
def step_impl_given_with_objectid(context, resource):
    data = apply_placeholders(context, context.text)
    with context.app.test_request_context(context.app.config["URL_PREFIX"]):
        items = [parse(item, resource) for item in json.loads(data)]
        for item in items:
            if "_id" in item:
                item["_id"] = ObjectId(item["_id"])

        get_resource_service(resource).post(items)
        context.data = items
        context.resource = resource
        setattr(context, resource, items[-1])


@given('the "{resource}"')
def step_impl_given_the(context, resource):
    with context.app.test_request_context(context.app.config["URL_PREFIX"]):
        if not is_user_resource(resource):
            get_resource_service(resource).delete_action()

        orig_items = {}
        items = [parse(item, resource) for item in json.loads(context.text)]
        get_resource_service(resource).post(items)
        context.data = orig_items or items
        context.resource = resource


@given('ingest from "{provider}"')
def step_impl_given_resource_with_provider(context, provider):
    resource = "ingest"
    with context.app.test_request_context(context.app.config["URL_PREFIX"]):
        get_resource_service(resource).delete_action()
        items = [parse(item, resource) for item in json.loads(context.text)]
        ingest_provider = get_resource_service("ingest_providers").find_one(req=None, _id=context.providers[provider])
        for item in items:
            item["ingest_provider"] = context.providers[provider]
            item["source"] = ingest_provider.get("source")
        get_resource_service(resource).post(items)
        context.data = items
        context.resource = resource


@given("config update")
def given_config_update(context):
    tests.update_config_from_step(context, json.loads(context.text))


@given("config")
def step_impl_given_config(context):
    tests.setup(context, json.loads(context.text))
    tests.setup_auth_user(context)


@given('we have "{role_name}" role')
def step_impl_given_role(context, role_name):
    with context.app.test_request_context(context.app.config["URL_PREFIX"]):
        role = get_resource_service("roles").find_one(name=role_name, req=None)
        data = MongoJSONEncoder().encode({"role": role.get("_id")})
    response = patch_current_user(context, data)
    assert_ok(response)


@given('we have "{user_type}" as type of user')
def step_impl_given_user_type(context, user_type):
    with context.app.test_request_context(context.app.config["URL_PREFIX"]):
        data = json.dumps({"user_type": user_type})
    response = patch_current_user(context, data)
    assert_ok(response)


@when("we post to auth_db")
def step_impl_when_auth(context):
    data = context.text
    context.response = context.client.post(
        get_prefixed_url(context.app, "/auth_db"), data=data, headers=context.headers
    )
    if context.response.status_code == 200 or context.response.status_code == 201:
        item = json.loads(context.response.get_data())
        if item.get("_id"):
            set_placeholder(context, "AUTH_ID", item["_id"])
        context.headers.append(("Authorization", b"basic " + b64encode(item["token"].encode("ascii") + b":")))
        context.user = item["user"]


@when("we sleep for {limit}s")
def when_we_sleep_for(context, limit):
    time.sleep(int(limit))


@given('we create a new macro "{macro_name}"')
def step_create_new_macro(context, macro_name):
    src = get_fixture_path(context, macro_name)
    dst = get_macro_path(macro_name)
    shutil.copyfile(src, dst)


@when('we fetch from "{provider_name}" ingest "{guid}"')
def step_impl_fetch_from_provider_ingest(context, provider_name, guid):
    with context.app.test_request_context(context.app.config["URL_PREFIX"]):
        fetch_from_provider(context, provider_name, guid)


@when('we fetch from "{provider_name}" ingest "{guid}" (mocking with "{mock_file}")')
def step_impl_fetch_from_provider_ingest_with_mocking(context, provider_name, guid, mock_file):
    with context.app.test_request_context(context.app.config["URL_PREFIX"]):
        ingest_provider_service = get_resource_service("ingest_providers")
        provider = ingest_provider_service.find_one(name=provider_name, req=None)

        with responses.RequestsMock() as rsps:
            apply_mock_file(rsps, mock_file, fixture_path=get_provider_file_path(provider))
            fetch_from_provider(context, provider_name, guid)


@when('we run update_ingest command for "{provider_name}"')
def step_impl_run_update_ingest_command(context, provider_name):
    with context.app.test_request_context(context.app.config["URL_PREFIX"]):
        ingest_provider_service = get_resource_service("ingest_providers")

        # close other providers except `provider_name`
        for provider in [p for p in context.providers if p != provider_name]:
            ingest_provider_service.patch(context.providers[provider], {"is_closed": True})
        provider = ingest_provider_service.find_one(name=provider_name, req=None)

        if provider["feeding_service"] == "ftp":
            run_update_ingest_ftp()
        else:
            # TODO for FTP feeding service all needed objects were patched/mocked
            # for other feeding services it must be implemented
            update_ingest.UpdateIngest().run()


@mock.patch.object(ftp, "ftp_connect", return_value=mock.MagicMock())
@mock.patch.object(update_ingest, "is_scheduled", return_value=True)
def run_update_ingest_ftp(*args):
    def retrieve_and_parse_side_effect(ftp, config, filename, provider, registered_parser):
        created = datetime.now() + timedelta(days=365)
        item1 = {
            "guid": "20170825001315282181",
            "type": "text",
            "uri": None,
            "usageterms": "Usage",
            "headline": "headline 1",
            "copyrightnotice": "Copyright",
            "urgency": 1,
            "pubstatus": "usable",
            "copyrightholder": "Australian Associated Press",
            "ednote": "ed note 1",
            "body_html": "<p>The story so far.</p>",
            "slugline": "slugline",
            "source": "AAP",
            "byline": "Peter and Jane",
            "description_text": "abstract",
            "profile": "ContentProfile",
            "priority": 6,
            "genre": [{"name": "Article (news)", "qcode": "Article"}],
            "anpa_category": [{"name": "International News", "qcode": "i"}],
            "subject": [{"name": "arts, culture and entertainment", "qcode": "01000000"}],
            "versioncreated": created,
            "firstcreated": created,
            "dateline": {"located": {"city": "Milton Keynes"}},
            "abstract": "abstract",
            "place": [{"name": "NSW", "qcode": "NSW"}],
            "authors": [{"name": "John", "role": "writer", "avatar_url": "http://example.com", "biography": "bio"}],
        }
        if filename == "ninjs1.json":
            return [item1]
        elif filename == "ninjs2.json":
            item2 = deepcopy(item1)
            item2["guid"] = "20170825001315282182"
            item2["headline"] = "headline 2"
            item2["ednote"] = "ed note 2"
            return [item2]
        elif filename == "ninjs3.json":
            item3 = deepcopy(item1)
            item3["guid"] = "20170825001315282183"
            item3["headline"] = "headline 3"
            item3["ednote"] = "ed note 3"
            return [item3]

    with mock.patch.object(ftp.FTPFeedingService, "_list_files") as ftp_list_files_mock:
        ftp_list_files_mock.return_value = (
            ("ninjs1.json", "20181111123456"),
            ("ninjs2.json", "20181111123456"),
            ("ninjs3.json", "20181111123456"),
        )
        with mock.patch.object(
            ftp.FTPFeedingService, "_retrieve_and_parse"
        ) as retrieve_and_parse_mock, mock.patch.object(ftp.FTPFeedingService, "_is_empty") as empty_file_mock:
            retrieve_and_parse_mock.side_effect = retrieve_and_parse_side_effect
            empty_file_mock.return_value = False
            # run command
            update_ingest.UpdateIngest().run()


def embed_routing_scheme_rules(scheme):
    """Fetch all content filters referenced by the given routing scheme and embed those into scheme.

    :param dict scheme: routing scheme configuration
    """
    filters_service = superdesk.get_resource_service("content_filters")

    rules_filters = ((rule, str(rule["filter"])) for rule in scheme["rules"] if rule.get("filter"))

    for rule, filter_id in rules_filters:
        content_filter = filters_service.find_one(_id=filter_id, req=None)
        rule["filter"] = content_filter


@when('we fetch from "{provider_name}" ingest "{guid}" using routing_scheme')
def step_impl_fetch_from_provider_ingest_using_routing(context, provider_name, guid):
    with context.app.test_request_context(context.app.config["URL_PREFIX"]):
        _id = apply_placeholders(context, context.text)
        routing_scheme = get_resource_service("routing_schemes").find_one(_id=_id, req=None)
        embed_routing_scheme_rules(routing_scheme)
        fetch_from_provider(context, provider_name, guid, routing_scheme)


@when('we ingest and fetch "{provider_name}" "{guid}" to desk "{desk}" stage "{stage}" using routing_scheme')
def step_impl_fetch_from_provider_ingest_using_routing_with_desk(context, provider_name, guid, desk, stage):
    with context.app.test_request_context(context.app.config["URL_PREFIX"]):
        _id = apply_placeholders(context, context.text)
        desk_id = apply_placeholders(context, desk)
        stage_id = apply_placeholders(context, stage)
        routing_scheme = get_resource_service("routing_schemes").find_one(_id=_id, req=None)
        embed_routing_scheme_rules(routing_scheme)
        fetch_from_provider(context, provider_name, guid, routing_scheme, desk_id, stage_id)


@when('we ingest with routing scheme "{provider_name}" "{guid}"')
def step_impl_ingest_with_routing_scheme(context, provider_name, guid):
    with context.app.test_request_context(context.app.config["URL_PREFIX"]):
        _id = apply_placeholders(context, context.text)
        routing_scheme = get_resource_service("routing_schemes").find_one(_id=_id, req=None)
        embed_routing_scheme_rules(routing_scheme)
        fetch_from_provider(context, provider_name, guid, routing_scheme)


def get_provider_file_path(provider, filename=""):
    if provider.get("name", "").lower() == "ftp_ninjs":
        return os.path.join(provider.get("config", {}).get("path_fixtures", ""), filename)
    else:
        return os.path.join(provider.get("config", {}).get("path", ""), filename)


def fetch_from_provider(context, provider_name, guid, routing_scheme=None, desk_id=None, stage_id=None):
    ingest_provider_service = get_resource_service("ingest_providers")
    provider = ingest_provider_service.find_one(name=provider_name, req=None)
    provider["routing_scheme"] = routing_scheme
    if "rule_set" in provider:
        rule_set = get_resource_service("rule_sets").find_one(_id=provider["rule_set"], req=None)
    else:
        rule_set = None

    provider_service = get_feeding_service(provider["feeding_service"])

    if provider.get("name", "").lower() in ("aap", "dpa", "ninjs", "email", "ftp_ninjs", "stt"):
        if provider.get("name", "").lower() == "ftp_ninjs":
            file_path = os.path.join(provider.get("config", {}).get("path_fixtures", ""), guid)
        else:
            file_path = os.path.join(provider.get("config", {}).get("path", ""), guid)
        feeding_parser = provider_service.get_feed_parser(provider)
        if isinstance(feeding_parser, STTNewsMLFeedParser):
            with open(file_path, "rb") as f:
                xml_string = etree.etree.fromstring(f.read())
                items = feeding_parser.parse(xml_string, provider)
        elif isinstance(feeding_parser, XMLFeedParser):
            with open(file_path, "rb") as f:
                xml_string = etree.etree.fromstring(f.read())
                items = [feeding_parser.parse(xml_string, provider)]
        elif isinstance(feeding_parser, EMailRFC822FeedParser):
            with open(file_path, "rb") as f:
                data = f.read()
                items = feeding_parser.parse([(1, data)], provider)
        else:
            parsed = feeding_parser.parse(file_path, provider)
            items = [parsed] if not isinstance(parsed, list) else parsed
    else:
        provider_service.provider = provider
        provider_service.URL = provider.get("config", {}).get("url")
        items = provider_service.fetch_ingest(guid)

    for item in items:
        item["versioncreated"] = utcnow()
        item["expiry"] = utcnow() + timedelta(minutes=20)

        if desk_id:
            from bson.objectid import ObjectId

            item["task"] = {"desk": ObjectId(desk_id), "stage": ObjectId(stage_id)}

    failed = context.ingest_items(
        items, provider, provider_service, rule_set=rule_set, routing_scheme=provider.get("routing_scheme")
    )
    assert len(failed) == 0, failed

    provider = ingest_provider_service.find_one(name=provider_name, req=None)
    ingest_provider_service.system_update(provider["_id"], {LAST_ITEM_UPDATE: utcnow()}, provider)

    for item in items:
        set_placeholder(context, "{}.{}".format(provider_name, item["guid"]), item["_id"])


def apply_mock_file(rsps, mock_file, fixture_path=None):
    """Parse the mock file and apply it

    This must be executed inside a responses context.
    :param rsps: responses context object
    :param mock_file: name of the mock_file (inside fixture path)
    :param fixture_path: path to the directory containing the file for "binary"
    """
    mock_file = os.path.join(str(fixture_path), mock_file)
    with open(mock_file) as f:
        mocks = json.load(f)
    for mock_url, mock_data in mocks.get("requests", {}).items():
        for verb, verb_data in mock_data.items():
            verb = verb.upper()

            if verb != "GET":
                raise NotImplementedError('we only support mocking "get" for now')
            kwargs = {}

            if "text" in verb_data:
                kwargs["body"] = verb_data["text"]
                content_type = verb_data.get("content_type", "text/plain")
            elif "json" in verb_data:
                kwargs["json"] = verb_data["json"]
                content_type = verb_data.get("content_type", "application/json")
            elif "binary" in verb_data:
                binary_file = verb_data["binary"]
                # we have a binary file to return
                binary_path = os.path.join(str(fixture_path), binary_file)
                with open(binary_path, "rb") as f:
                    kwargs["body"] = f.read()
                content_type = verb_data.get("content_type", "application/octet-stream")

            rsps.add(verb, mock_url, content_type=content_type, **kwargs)


@when('we post to "{url}"')
def step_impl_when_post_url(context, url):
    post_data(context, url)


@when('we post to "{url}" with delay')
def step_impl_when_post_url_delay(context, url):
    time.sleep(1)
    post_data(context, url)


def set_user_default(url, data):
    if is_user_resource(url):
        user = json.loads(data)
        user.setdefault("needs_activation", False)
        data = json.dumps(user)


def get_response_etag(response):
    return json.loads(response.get_data())["_etag"]


@then("we save etag")
def step_when_we_save_etag(context):
    context.etag = get_response_etag(context.response)


@then("we get matching etag")
def step_then_we_get_same_etag(context):
    assert context.etag == get_response_etag(context.response), "etags not matching %s != %s" % (
        context.etag,
        get_response_etag(context.response),
    )


@then("we get different etag")
def step_then_we_get_different_etag(context):
    assert context.etag != get_response_etag(context.response), "etags are matching"


def store_placeholder(context, url):
    if context.response.status_code in (200, 201):
        try:
            item = json.loads(context.response.get_data())
        except ValueError:
            assert False, context.response.get_data()
        if item["_status"] == "OK" and item.get("_id"):
            try:
                setattr(context, get_resource_name(url), item)
                context.placeholders = getattr(context, "placeholders", {})
                context.placeholders[get_resource_name(url)] = item
            except (IndexError, KeyError):
                pass


def post_data(context, url, success=False):
    with context.app.mail.record_messages() as outbox:
        data = apply_placeholders(context, context.text)
        url = apply_placeholders(context, url)
        set_user_default(url, data)
        context.response = context.client.post(get_prefixed_url(context.app, url), data=data, headers=context.headers)
        if success:
            assert_ok(context.response)

        item = json.loads(context.response.get_data())
        context.outbox = outbox
        store_placeholder(context, url)
        return item


@when('we post to "{url}" with "{tag}" and success')
def step_impl_when_post_url_with_tag(context, url, tag):
    item = post_data(context, url, True)
    if item.get("_id"):
        set_placeholder(context, tag, item.get("_id"))


@given('we have "{url}" with "{tag}" and success')
def step_impl_given_post_url_with_tag(context, url, tag):
    item = post_data(context, url, True)
    if item.get("_id"):
        set_placeholder(context, tag, item.get("_id"))


@when('we post to "{url}" with success')
def step_impl_when_post_url_with_success(context, url):
    post_data(context, url, True)


@when('we put to "{url}"')
def step_impl_when_put_url(context, url):
    with context.app.mail.record_messages() as outbox:
        url = apply_placeholders(context, url)
        res = get_res(url, context)
        headers = if_match(context, res.get("_etag"))
        data = apply_placeholders(context, context.text)
        href = get_prefixed_url(context.app, url)
        context.response = context.client.put(href, data=data, headers=headers)
        context.outbox = outbox


@when('we get "{url}"')
def when_we_get_url(context, url):
    url = apply_placeholders(context, url).encode("ascii").decode("unicode-escape")
    headers = []
    if context.text:
        for line in context.text.split("\n"):
            key, val = line.split(": ")
            headers.append((key, val))
    headers = unique_headers(headers, context.headers)
    url = apply_placeholders(context, url)
    context.response = context.client.get(get_prefixed_url(context.app, url), headers=headers)


@when('we get dictionary "{dictionary_id}"')
def when_we_get_dictionary(context, dictionary_id):
    dictionary_id = apply_placeholders(context, dictionary_id)
    url = "/dictionaries/" + dictionary_id + '?projection={"content": 1}'
    return when_we_get_url(context, url)


@then("we get latest")
def step_impl_we_get_latest(context):
    data = get_json_data(context.response)
    href = get_self_href(data, context)
    headers = if_match(context, data.get("_etag"))
    href = get_prefixed_url(context.app, href)
    context.response = context.client.get(href, headers=headers)
    assert_200(context.response)


@when('we find for "{resource}" the id as "{name}" by "{search_criteria}"')
def when_we_find_for_resource_the_id_as_name_by_search_criteria(context, resource, name, search_criteria):
    url = "/" + resource + "?" + search_criteria
    context.response = context.client.get(get_prefixed_url(context.app, url), headers=context.headers)
    if context.response.status_code == 200:
        expect_json_length(context.response, 1, path="_items")
        item = json.loads(context.response.get_data())
        item = item["_items"][0]
        if item.get("_id"):
            set_placeholder(context, name, item["_id"])


@when('we delete "{url}"')
def step_impl_when_delete_url(context, url):
    with context.app.mail.record_messages() as outbox:
        url = apply_placeholders(context, url)
        res = get_res(url, context)
        href = get_self_href(res, context)
        headers = if_match(context, res.get("_etag"))
        href = get_prefixed_url(context.app, href)
        context.response = context.client.delete(href, headers=headers)
        context.outbox = outbox


@when('we delete link "{url}"')
def step_impl_when_delete_link_url(context, url):
    with context.app.mail.record_messages() as outbox:
        url = apply_placeholders(context, url)
        headers = context.headers
        context.response = context.client.delete(get_prefixed_url(context.app, url), headers=headers)
        context.outbox = outbox


@when('we delete all sessions "{url}"')
def step_impl_when_delete_all_url(context, url):
    with context.app.mail.record_messages() as outbox:
        url = apply_placeholders(context, url)
        headers = context.headers
        href = get_prefixed_url(context.app, url)
        context.response = context.client.delete(href, headers=headers)
        context.outbox = outbox


@when("we delete latest")
def when_we_delete_it(context):
    with context.app.mail.record_messages() as outbox:
        res = get_json_data(context.response)
        href = get_self_href(res, context)
        headers = if_match(context, res.get("_etag"))
        href = get_prefixed_url(context.app, href)
        context.response = context.client.delete(href, headers=headers)
        context.email = outbox


@when('we patch "{url}"')
def step_impl_when_patch_url(context, url):
    with context.app.mail.record_messages() as outbox:
        url = apply_placeholders(context, url)
        res = get_res(url, context)
        href = get_self_href(res, context)
        headers = if_match(context, res.get("_etag"))
        data = apply_placeholders(context, context.text)
        href = get_prefixed_url(context.app, href)
        context.response = context.client.patch(href, data=data, headers=headers)
        context.outbox = outbox


@when("we patch latest")
def step_impl_when_patch_again(context):
    with context.app.mail.record_messages() as outbox:
        data = get_json_data(context.response)
        href = get_prefixed_url(context.app, get_self_href(data, context))
        headers = if_match(context, data.get("_etag"))
        data2 = apply_placeholders(context, context.text)
        context.response = context.client.patch(href, data=data2, headers=headers)
        if context.response.status_code in (200, 201):
            item = json.loads(context.response.get_data())
            if item["_status"] == "OK" and item.get("_id"):
                setattr(context, get_resource_name(href), item)
        assert_ok(context.response)
        context.outbox = outbox


@when("we patch latest without assert")
def step_impl_when_patch_without_assert(context):
    data = get_json_data(context.response)
    href = get_prefixed_url(context.app, get_self_href(data, context))
    headers = if_match(context, data.get("_etag"))
    data2 = apply_placeholders(context, context.text)
    context.response = context.client.patch(href, data=data2, headers=headers)


@when('we patch routing scheme "{url}"')
def step_impl_when_patch_routing_scheme(context, url):
    with context.app.mail.record_messages() as outbox:
        url = apply_placeholders(context, url)
        res = get_res(url, context)
        href = get_self_href(res, context)
        headers = if_match(context, res.get("_etag"))
        data = json.loads(apply_placeholders(context, context.text))
        res.get("rules", []).append(data)
        context.response = context.client.patch(
            get_prefixed_url(context.app, href), data=json.dumps({"rules": res.get("rules", [])}), headers=headers
        )
        context.outbox = outbox


@when("we patch given")
def step_impl_when_patch(context):
    with context.app.mail.record_messages() as outbox:
        href, etag = get_it(context)
        headers = if_match(context, etag)
        context.response = context.client.patch(get_prefixed_url(context.app, href), data=context.text, headers=headers)
        assert_ok(context.response)
        context.outbox = outbox


@when("we get given")
def step_impl_when_get(context):
    href, _etag = get_it(context)
    context.response = context.client.get(get_prefixed_url(context.app, href), headers=context.headers)


@when("we restore version {version}")
def step_impl_when_restore_version(context, version):
    data = get_json_data(context.response)
    href = get_self_href(data, context)
    headers = if_match(context, data.get("_etag"))
    text = '{"type": "text", "old_version": %s, "last_version": %s}' % (version, data.get("_current_version"))
    context.response = context.client.put(get_prefixed_url(context.app, href), data=text, headers=headers)
    assert_ok(context.response)


@when('we upload a file "{filename}" to "{dest}"')
def step_impl_when_upload_image(context, filename, dest):
    data = {} if not context.text else json.loads(apply_placeholders(context, context.text))
    upload_file(context, dest, filename, "media", data)


@when("we upload a binary file with cropping")
def step_impl_when_upload_with_crop(context):
    data = {"CropTop": "0", "CropLeft": "0", "CropBottom": "333", "CropRight": "333"}
    upload_file(context, "/upload", "bike.jpg", "media", data)


@when('upload a file "{file_name}" to "{destination}" with "{guid}"')
def step_impl_when_upload_image_with_guid(context, file_name, destination, guid):
    metadata = {
        "guid": guid,
        "headline": file_name,
        "alt_text": file_name,
        "description_text": file_name,
    }
    upload_file(context, destination, file_name, "media", metadata)
    if destination == "archive":
        set_placeholder(context, "original.href", context.archive["renditions"]["original"]["href"])
        set_placeholder(context, "original.media", context.archive["renditions"]["original"]["media"])


@when("we upload a new dictionary with success")
def when_upload_dictionary(context):
    data = json.loads(apply_placeholders(context, context.text))
    upload_file(context, "/dictionaries", "test_dict.txt", DICTIONARY_FILE, data)
    assert_ok(context.response)


@when("we upload to an existing dictionary with success")
def when_upload_patch_dictionary(context):
    data = json.loads(apply_placeholders(context, context.text))
    url = apply_placeholders(context, "/dictionaries/#dictionaries._id#")
    etag = apply_placeholders(context, "#dictionaries._etag#")
    upload_file(context, url, "test_dict2.txt", DICTIONARY_FILE, data, "patch", [("If-Match", etag)])
    assert_ok(context.response)


def upload_file(context, dest, filename, file_field, extra_data=None, method="post", user_headers=None):
    if user_headers is None:
        user_headers = []
    with open(get_fixture_path(context, filename), "rb") as f:
        data = {file_field: f}
        if extra_data:
            data.update(extra_data)
        headers = [("Content-Type", "multipart/form-data")]
        headers.extend(user_headers)
        headers = unique_headers(headers, context.headers)
        url = get_prefixed_url(context.app, dest)
        context.response = getattr(context.client, method)(url, data=data, headers=headers)
        assert_ok(context.response)
        store_placeholder(context, url)


@when("we upload a file from URL")
def step_impl_when_upload_from_url(context):
    data = {"URL": external_url}
    headers = [("Content-Type", "multipart/form-data")]
    headers = unique_headers(headers, context.headers)
    fixture_path = Path(superdesk.__file__).parent.parent / "tests" / "io" / "fixtures"

    with responses.RequestsMock() as rsps:
        apply_mock_file(rsps, "upload_from_url_mock.json", fixture_path=fixture_path)
        context.response = context.client.post(get_prefixed_url(context.app, "/upload"), data=data, headers=headers)


@when("we upload a file from URL with cropping")
def step_impl_when_upload_from_url_with_crop(context):
    data = {"URL": external_url, "CropTop": "0", "CropLeft": "0", "CropBottom": "333", "CropRight": "333"}
    headers = [("Content-Type", "multipart/form-data")]
    headers = unique_headers(headers, context.headers)
    fixture_path = Path(superdesk.__file__).parent.parent / "tests" / "io" / "fixtures"

    with responses.RequestsMock() as rsps:
        apply_mock_file(rsps, "upload_from_url_mock.json", fixture_path=fixture_path)
        context.response = context.client.post(get_prefixed_url(context.app, "/upload"), data=data, headers=headers)


@when("we get user profile")
def step_impl_when_get_user(context):
    profile_url = "/%s/%s" % ("users", context.user["_id"])
    context.response = context.client.get(get_prefixed_url(context.app, profile_url), headers=context.headers)


@then("we get new resource")
def step_impl_then_get_new(context):
    assert_ok(context.response)
    expect_json_contains(context.response, "self", path="_links")
    if context.text is not None:
        return test_json(context)


@then("we get error {code}")
def step_impl_then_get_error(context, code):
    expect_status(context.response, int(code))
    if context.text:
        print("got", context.response.get_data().decode("utf-8"))
        test_json(context)


@then("we get list with {total_count} {unit}")
def step_impl_then_get_list(context, total_count, unit=None):
    assert_200(context.response)
    data = get_json_data(context.response)
    int_count = int(total_count.replace("+", "").replace("<", ""))

    if "+" in total_count:
        assert int_count <= data["_meta"]["total"], "%d items is not enough" % data["_meta"]["total"]
    elif total_count.startswith("<"):
        assert int_count > data["_meta"]["total"], "%d items is too much" % data["_meta"]["total"]
    else:
        assert int_count == data["_meta"]["total"], "got %d: %s" % (
            data["_meta"]["total"],
            format_items(data["_items"]),
        )
    if context.text:
        test_json(context)

    set_placeholder(context, "items", data["_items"])


@then("we get list ordered by {field} with {total_count} items")
def step_impl_ordered_by_field_list(context, field, total_count):
    step_impl_then_get_list(context, total_count)
    data = get_json_data(context.response)
    items = data["_items"]
    assert sorted(items, key=operator.itemgetter(field)) == items


@then("we get ordered list with {total_count} items")
def step_impl_get_ordered_list(context, total_count):
    step_impl_then_get_list(context, total_count)
    data = get_json_data(context.response)
    server_items = data["_items"]
    context_items = json.loads(apply_placeholders(context, context.text))["_items"]
    idgetter = operator.itemgetter("_id")
    server_sorted = list(map(idgetter, server_items))
    context_sorted = list(map(idgetter, context_items))
    assert server_sorted == context_sorted, "server items are not sorted: %s" % server_sorted


@then('we get "{value}" in formatted output')
def step_impl_then_get_formatted_output(context, value):
    assert_200(context.response)
    value = apply_placeholders(context, value)
    data = get_json_data(context.response)
    for item in data["_items"]:
        if value in item["formatted_item"]:
            return
    assert False


@then('we get "{value}" in formatted output as "{group}" story for subscriber "{sub}"')
def step_impl_then_get_formatted_output_as_story(context, value, group, sub):
    assert_200(context.response)
    value = apply_placeholders(context, value)
    data = get_json_data(context.response)
    for item in data["_items"]:
        if item["subscriber_id"] != sub:
            continue

        try:
            formatted_data = json.loads(item["formatted_item"])
        except Exception:
            continue

        associations = formatted_data.get("associations", {})
        for assoc_group in associations:
            if assoc_group.startswith(group) and associations[assoc_group].get("guid", "") == value:
                return
    assert False


@then('we get "{value}" as "{group}" story for subscriber "{sub}" in package "{pck}"')
def step_impl_then_get_formatted_output_pck(context, value, group, sub, pck):
    assert_200(context.response)
    value = apply_placeholders(context, value)
    data = get_json_data(context.response)
    for item in data["_items"]:
        if item["item_id"] != pck:
            continue

        if item["subscriber_id"] != sub:
            continue

        try:
            formatted_data = json.loads(item["formatted_item"])
        except Exception:
            continue

        associations = formatted_data.get("associations", {})
        for assoc_group in associations:
            if assoc_group.startswith(group) and associations[assoc_group].get("guid", "") == value:
                return
    assert False


@then('we get "{value}" as "{group}" story for subscriber "{sub}" not in package "{pck}" version "{v}"')
def step_impl_then_get_formatted_output_pck_version(context, value, group, sub, pck, v):
    assert_200(context.response)
    value = apply_placeholders(context, value)
    data = get_json_data(context.response)
    for item in data["_items"]:
        if item["item_id"] == pck:
            if item["subscriber_id"] == sub and str(item["item_version"]) == v:
                try:
                    formatted_data = json.loads(item["formatted_item"])
                except Exception:
                    continue

                associations = formatted_data.get("associations", {})
                for assoc_group in associations:
                    if assoc_group.startswith(group) and associations[assoc_group].get("guid", "") == value:
                        assert False

                assert True
                return
    assert False


@then('we get "{value}" in formatted output as "{group}" newsml12 story')
def step_impl_then_get_formatted_output_newsml(context, value, group):
    assert_200(context.response)
    value = apply_placeholders(context, value)
    data = get_json_data(context.response)
    for item in data["_items"]:
        if "<" + group + ">" + value + "</" + group + ">" in item["formatted_item"]:
            return
    assert False


@then('we get no "{field}"')
def step_impl_then_get_nofield(context, field):
    assert_200(context.response)
    expect_json_not_contains(context.response, field)


@then('expect json in "{path}"')
def step_impl_then_get_nofield_in_path(context, path):
    assert_200(context.response)
    expect_json(context.response, context.text, path)


@then("we get existing resource")
def step_impl_then_get_existing(context):
    assert_200(context.response)
    print("got", get_response_readable(context.response.data))
    test_json(context)


@then("we get existing saved search")
def step_impl_then_get_existing_saved_search(context):
    assert_200(context.response)
    test_json_with_string_field_value(context, "filter")


@then("we get OK response")
def step_impl_then_get_ok(context):
    assert_200(context.response)
    if context.text:
        test_json(context)


@then("we get response code {code}")
def step_impl_then_get_code(context, code):
    assert context.response.status_code == int(code), "we got code={} data={}".format(
        context.response.status_code, get_response_readable(context.response.data)
    )
    if context.text:
        test_json(context)


@then("we get updated response")
def step_impl_then_get_updated(context):
    assert_ok(context.response)
    if context.text:
        test_json(context)


@then('we get "{key}" in "{url}"')
def step_impl_then_get_key_in_url(context, key, url):
    url = apply_placeholders(context, url)
    res = context.client.get(get_prefixed_url(context.app, url), headers=context.headers)
    assert_200(res)
    expect_json_contains(res, key)


@then("we get file metadata")
def step_impl_then_get_file_meta(context):
    assert len(json.loads(apply_path(parse_json_response(context.response), "filemeta_json")).items()) > 0
    "expected non empty metadata dictionary"


@then('we get "{filename}" metadata')
def step_impl_then_get_given_file_meta(context, filename):
    if filename == "bike.jpg":
        metadata = {
            "ycbcrpositioning": 1,
            "imagelength": 2448,
            "exifimagewidth": 2448,
            "meteringmode": 2,
            "datetimedigitized": "2013:08:01 16:19:28",
            "exposuremode": 0,
            "flashpixversion": "0100",
            "isospeedratings": 80,
            "length": 469900,
            "imageuniqueid": "f3533c05daef2debe6257fd99e058eec",
            "datetimeoriginal": "2013:08:01 16:19:28",
            "whitebalance": 0,
            "exposureprogram": 3,
            "colorspace": 1,
            "exifimageheight": 3264,
            "software": "Google",
            "resolutionunit": 2,
            "make": "SAMSUNG",
            "maxaperturevalue": [276, 100],
            "aperturevalue": [276, 100],
            "scenecapturetype": 0,
            "exposuretime": [1, 2004],
            "datetime": "2013:08:01 16:19:28",
            "exifoffset": 216,
            "yresolution": [72, 1],
            "orientation": 1,
            "componentsconfiguration": "0000",
            "exifversion": "0220",
            "focallength": [37, 10],
            "flash": 0,
            "model": "GT-I9300",
            "xresolution": [72, 1],
            "fnumber": [26, 10],
            "imagewidth": 3264,
            "brightnessvalue": [2362, 256],
            "exposurebiasvalue": [0, 10],
            "shutterspeedvalue": [2808, 256],
        }
    elif filename == "green.ogg":
        metadata = {
            "producer": "Lavf54.59.103",
            "music_genre": "New Age",
            "sample_rate": "44100",
            "artist": "Maxime Abbey",
            "length": 368058,
            "bit_rate": "160000",
            "title": "Green Hills",
            "mime_type": "audio/vorbis",
            "format_version": "Vorbis version 0",
            "compression": "Vorbis",
            "duration": "0:00:20.088163",
            "endian": "Little endian",
            "nb_channel": "2",
        }
    elif filename == "this_week_nasa.mp4":
        metadata = {
            "mime_type": "video/mp4",
            "creation_date": "1904-01-01T00:00:00+00:00",
            "duration": "0:00:10.224000",
            "width": "480",
            "length": 877869,
            "comment": "User volume: 100.0%",
            "height": "270",
            "endian": "Big endian",
            "last_modification": "1904-01-01T00:00:00+00:00",
        }
    else:
        raise NotImplementedError("No metadata for file '{}'.".format(filename))

    assertions.maxDiff = None
    data = json.loads(context.response.get_data())
    filemeta = get_filemeta(data)
    json_match(filemeta, metadata)


@then('we get "{type}" renditions')
def step_impl_then_get_renditions(context, type):
    expect_json_contains(context.response, "renditions")
    renditions = apply_path(parse_json_response(context.response), "renditions")
    assert isinstance(renditions, dict), "expected dict for image renditions"
    for rend_name in context.app.config["RENDITIONS"][type]:
        desc = renditions[rend_name]
        assert isinstance(desc, dict), "expected dict for rendition description"
        assert "href" in desc, "expected href in rendition description"
        assert "media" in desc, "expected media identifier in rendition description"
        we_can_fetch_a_file(context, desc["href"], "image/jpeg")


@then('we get "{crop_name}" in renditions')
def step_impl_then_get_crop_renditions(context, crop_name):
    expect_json_contains(context.response, "renditions")
    renditions = apply_path(parse_json_response(context.response), "renditions")
    assert isinstance(renditions, dict), "expected dict for image renditions"
    desc = renditions[crop_name]
    assert isinstance(desc, dict), "expected dict for rendition description"
    assert "href" in desc, "expected href in rendition description"
    assert "media" in desc, "expected media identifier in rendition description"
    we_can_fetch_a_file(context, desc["href"], "image/jpeg")


@then('we get "{crop_name}" not in renditions')
def step_impl_then_crop_not_in_renditions(context, crop_name):
    expect_json_contains(context.response, "renditions")
    renditions = apply_path(parse_json_response(context.response), "renditions")
    assert isinstance(renditions, dict), "expected dict for image renditions"
    assert crop_name not in renditions, "expected crop not in renditions"


@then('item "{item_id}" is unlocked')
def then_item_is_unlocked(context, item_id):
    assert_200(context.response)
    data = json.loads(context.response.get_data())
    assert data.get("lock_user", None) is None, "item is locked by user #{0}".format(data.get("lock_user"))


@then('item "{item_id}" is locked')
def then_item_is_locked(context, item_id):
    assert_200(context.response)
    resp = parse_json_response(context.response)
    assert resp["lock_user"] is not None


@then('item "{item_id}" is assigned')
def then_item_is_assigned(context, item_id):
    resp = parse_json_response(context.response)
    assert resp["task"].get("user", None) is not None, "item is not assigned"


@then('we get rendition "{name}" with mimetype "{mimetype}"')
def step_impl_then_get_rendition_with_mimetype(context, name, mimetype):
    expect_json_contains(context.response, "renditions")
    renditions = apply_path(parse_json_response(context.response), "renditions")
    assert isinstance(renditions, dict), "expected dict for image renditions"
    desc = renditions[name]
    assert isinstance(desc, dict), "expected dict for rendition description"
    assert "href" in desc, "expected href in rendition description"
    we_can_fetch_a_file(context, desc["href"], mimetype)
    set_placeholder(context, "rendition.{}.href".format(name), desc["href"])


@when("we get updated media from archive")
def get_updated_media_from_archive(context):
    url = "archive/%s" % context._id
    when_we_get_url(context, url)
    assert_200(context.response)


@then("baseImage rendition is updated")
def check_base_image_rendition(context):
    check_rendition(context, "baseImage")


@then('original rendition is updated with link to file having mimetype "{mimetype}"')
def check_original_rendition(context, mimetype):
    rv = parse_json_response(context.response)
    link_to_file = rv["renditions"]["original"]["href"]
    assert link_to_file
    we_can_fetch_a_file(context, link_to_file, mimetype)


@then("thumbnail rendition is updated")
def check_thumbnail_rendition(context):
    check_rendition(context, "thumbnail")


def check_rendition(context, rendition_name):
    rv = parse_json_response(context.response)
    assert rv["renditions"][rendition_name] != context.renditions[rendition_name], rv["renditions"]


@then('we get "{key}"')
def step_impl_then_get_key(context, key):
    assert_200(context.response)
    expect_json_contains(context.response, key)
    item = json.loads(context.response.get_data())
    set_placeholder(context, "%s" % key, item[key])


@then('we store "{key}" with value "{value}" to context')
def step_impl_then_we_store_key_value_to_context(context, key, value):
    set_placeholder(context, key, apply_placeholders(context, value))


@then("we get action in user activity")
def step_impl_then_get_action(context):
    response = context.client.get(get_prefixed_url(context.app, "/activity"), headers=context.headers)
    expect_json_contains(response, "_items")


@then("we get a file reference")
def step_impl_then_get_file(context):
    assert_200(context.response)
    expect_json_contains(context.response, "renditions")
    data = get_json_data(context.response)
    url = "/upload/%s" % data["_id"]
    headers = [("Accept", "application/json")]
    headers = unique_headers(headers, context.headers)
    response = context.client.get(get_prefixed_url(context.app, url), headers=headers)
    assert_200(response)
    assert len(response.get_data()), response
    assert response.mimetype == "application/json", response.mimetype
    expect_json_contains(response, "renditions")
    expect_json_contains(response, {"mimetype": "image/jpeg"})
    fetched_data = get_json_data(context.response)
    context.fetched_data = fetched_data


@then('we get cropped data smaller than "{max_size}"')
def step_impl_then_get_cropped_file(context, max_size):
    assert int(get_filemeta(context.fetched_data, "length")) < int(max_size), "was expecting smaller image"


@then("we can fetch a data_uri")
def step_impl_we_fetch_data_uri(context):
    we_can_fetch_a_file(context, context.fetched_data["renditions"]["original"]["href"], "image/jpeg")


@then('we fetch a file "{url}"')
def step_impl_we_cannot_fetch_file(context, url):
    url = apply_placeholders(context, url)
    assert "#" not in url, "missing placeholders for url %s %s" % (url, getattr(context, "placeholders", {}))
    headers = [("Accept", "application/json")]
    headers = unique_headers(headers, context.headers)
    context.response = context.client.get(get_prefixed_url(context.app, url), headers=headers)


def we_can_fetch_a_file(context, url, mimetype):
    headers = [("Accept", "application/json")]
    headers = unique_headers(headers, context.headers)
    response = context.client.get(get_prefixed_url(context.app, url), headers=headers)
    assert_200(response)
    assert len(response.get_data()), response
    assert response.mimetype == mimetype, response.mimetype


@then("we can delete that file")
def step_impl_we_delete_file(context):
    url = "/upload/%s" % context.fetched_data["_id"]
    context.headers.append(("Accept", "application/json"))
    headers = if_match(context, context.fetched_data.get("_etag"))
    response = context.client.delete(get_prefixed_url(context.app, url), headers=headers)
    assert_200(response)
    response = context.client.get(get_prefixed_url(context.app, url), headers=headers)
    assert_404(response)


@then("we get a picture url")
def step_impl_then_get_picture(context):
    assert_ok(context.response)
    expect_json_contains(context.response, "picture_url")


@then('we get aggregations "{keys}"')
def step_impl_then_get_aggs(context, keys):
    assert_200(context.response)
    expect_json_contains(context.response, "_aggregations")
    data = get_json_data(context.response)
    aggs = data["_aggregations"]
    for key in keys.split(","):
        assert_in(key, aggs)


@then("the file is stored localy")
def step_impl_then_file(context):
    assert_200(context.response)
    folder = context.app.config["UPLOAD_FOLDER"]
    assert os.path.exists(os.path.join(folder, context.filename))


@then("we get version {version}")
def step_impl_then_get_version(context, version):
    assert_200(context.response)
    expect_json_contains(context.response, {"_current_version": int(version)})


@then('the field "{field}" value is "{value}"')
def step_impl_then_get_field_value(context, field, value):
    assert_200(context.response)
    expect_json_contains(context.response, {field: value})


@then('we get etag matching "{url}"')
def step_impl_then_get_etag(context, url):
    if context.app.config["IF_MATCH"]:
        assert_200(context.response)
        expect_json_contains(context.response, "_etag")
        etag = get_json_data(context.response).get("_etag")
        response = context.client.get(get_prefixed_url(context.app, url), headers=context.headers)
        expect_json_contains(response, {"_etag": etag})


@then("we get not modified response")
def step_impl_then_not_modified(context):
    expect_status(context.response, 304)


@then('we get "{header}" header')
def step_impl_then_get_header(context, header):
    expect_headers_contain(context.response, header)


@then('we get "{header}" header with "{type}" type')
def step_impl_then_get_header_with_type(context, header, type):
    expect_headers_contain(context.response, header, type)


@then('we get link to "{resource}"')
def then_we_get_link_to_resource(context, resource):
    doc = get_json_data(context.response)
    self_link = doc.get("_links").get("self")
    assert resource in self_link["href"], 'expect link to "%s", got %s' % (resource, self_link)


@then("we get deleted response")
def then_we_get_deleted_response(context):
    assert_200(context.response)


@when('we post "{email}" to reset_password we get email with token')
def we_post_to_reset_password(context, email):
    data = {"email": email}
    headers = [("Content-Type", "multipart/form-data")]
    headers = unique_headers(headers, context.headers)
    with context.app.mail.record_messages() as outbox:
        context.response = context.client.post(
            get_prefixed_url(context.app, "/reset_user_password"), data=data, headers=headers
        )
        expect_status_in(context.response, (200, 201))
        assert len(outbox) == 1
        assert outbox[0].subject == "Reset password"
        email_text = outbox[0].body
        assert "24" in email_text
        words = email_text.split()
        url = urlparse(words[words.index("link") + 1])
        token = url.fragment.split("token=")[-1]
        assert token
        context.token = token


@then("we can check if token is valid")
def we_can_check_token_is_valid(context):
    data = {"token": context.token}
    headers = [("Content-Type", "multipart/form-data")]
    headers = unique_headers(headers, context.headers)
    context.response = context.client.post(
        get_prefixed_url(context.app, "/reset_user_password"), data=data, headers=headers
    )
    expect_status_in(context.response, (200, 201))


@then("we update token to be expired")
def we_update_token_to_expired(context):
    with context.app.test_request_context(context.app.config["URL_PREFIX"]):
        expiry = utc.utcnow() - timedelta(days=2)
        reset_request = get_resource_service("reset_user_password").find_one(req=None, token=context.token)
        reset_request["expire_time"] = expiry
        id = reset_request.pop("_id")
        get_resource_service("reset_user_password").patch(id, reset_request)


@then("token is invalid")
def check_token_invalid(context):
    data = {"token": context.token}
    headers = [("Content-Type", "multipart/form-data")]
    headers = unique_headers(headers, context.headers)
    context.response = context.client.post(
        get_prefixed_url(context.app, "/reset_user_password"), data=data, headers=headers
    )
    expect_status_in(context.response, (403, 401))


@when("we post to reset_password we do not get email with token")
def we_post_to_reset_password_it_fails(context):
    data = {"email": "foo@bar.org"}
    headers = [("Content-Type", "multipart/form-data")]
    headers = unique_headers(headers, context.headers)
    with context.app.mail.record_messages() as outbox:
        context.response = context.client.post(
            get_prefixed_url(context.app, "/reset_user_password"), data=data, headers=headers
        )
        expect_status_in(context.response, (200, 201))
        assert len(outbox) == 0


def start_reset_password_for_user(context):
    data = {"token": context.token, "password": "test_pass"}
    headers = [("Content-Type", "multipart/form-data")]
    headers = unique_headers(headers, context.headers)
    context.response = context.client.post(
        get_prefixed_url(context.app, "/reset_user_password"), data=data, headers=headers
    )


@then("we fail to reset password for user")
def we_fail_to_reset_password_for_user(context):
    start_reset_password_for_user(context)
    step_impl_then_get_error(context, 403)


@then("we reset password for user")
def we_reset_password_for_user(context):
    start_reset_password_for_user(context)
    expect_status_in(context.response, (200, 201))

    auth_data = {"username": "foo", "password": "test_pass"}
    headers = [("Content-Type", "multipart/form-data")]
    headers = unique_headers(headers, context.headers)
    context.response = context.client.post(get_prefixed_url(context.app, "/auth_db"), data=auth_data, headers=headers)
    expect_status_in(context.response, (200, 201))


@when("we switch user")
def when_we_switch_user(context):
    user = {
        "username": "test-user-2",
        "password": "pwd",
        "is_active": True,
        "needs_activation": False,
        "sign_off": "foo",
    }
    tests.setup_auth_user(context, user)
    set_placeholder(context, "USERS_ID", str(context.user["_id"]))


@when("we setup test user")
def when_we_setup_test_user(context):
    tests.setup_auth_user(context, tests.test_user)


@when('we get my "{url}"')
def when_we_get_my_url(context, url):
    user_id = str(context.user.get("_id"))
    my_url = "{0}?where={1}".format(url, json.dumps({"user": user_id}))
    return when_we_get_url(context, my_url)


@when('we get user "{resource}"')
def when_we_get_user_resource(context, resource):
    url = "/users/{0}/{1}".format(str(context.user.get("_id")), resource)
    return when_we_get_url(context, url)


@then("we get embedded items")
def we_get_embedded_items(context):
    response_data = json.loads(context.response.get_data())
    href = get_self_href(response_data, context)
    url = href + '/?embedded={"items": 1}'
    context.response = context.client.get(get_prefixed_url(context.app, url), headers=context.headers)
    assert_200(context.response)
    context.response_data = json.loads(context.response.get_data())
    assert len(context.response_data["items"]["view_items"]) == 2


@when("we reset notifications")
def step_when_we_reset_notifications(context):
    context.app.notification_client.reset()


@then("we get notifications")
def then_we_get_notifications(context):
    assert hasattr(context.app.notification_client, "messages"), "no messages"
    notifications = context.app.notification_client.messages
    notifications_data = [json.loads(notification) for notification in notifications]
    context_data = json.loads(apply_placeholders(context, context.text))
    assert_equal(
        json_match(context_data, notifications_data), True, msg=str(context_data) + "\n != \n" + str(notifications_data)
    )


@then("we get 0 notifications")
def then_we_get_no_notifications(context):
    notifications = getattr(context.app.notification_client, "messages", [])
    assert len(notifications) == 0, f"we got {len(notifications)} notifications: {notifications}"


@then("we get default preferences")
def get_default_prefs(context):
    response_data = json.loads(context.response.get_data())
    data = {}
    enhance_document_with_default_prefs(data)
    assert_equal(response_data["user_preferences"], data["user_preferences"])


@when('we spike "{item_id}"')
def step_impl_when_spike_url(context, item_id):
    item_id = apply_placeholders(context, item_id)
    res = get_res("/archive/" + item_id, context)
    headers = if_match(context, res.get("_etag"))

    context.response = context.client.patch(
        get_prefixed_url(context.app, "/archive/spike/" + item_id), data='{"state": "spiked"}', headers=headers
    )


@when("we spike fetched item")
def step_impl_when_spike_fetched_item(context):
    data = json.loads(apply_placeholders(context, context.text))
    item_id = data["_id"]
    res = get_res("/archive/" + item_id, context)
    headers = if_match(context, res.get("_etag"))

    context.response = context.client.patch(
        get_prefixed_url(context.app, "/archive/spike/" + item_id), data='{"state": "spiked"}', headers=headers
    )


@when('we unspike "{item_id}"')
def step_impl_when_unspike_url(context, item_id):
    item_id = apply_placeholders(context, item_id)
    res = get_res("/archive/" + item_id, context)
    headers = if_match(context, res.get("_etag"))
    context.response = context.client.patch(
        get_prefixed_url(context.app, "/archive/unspike/" + item_id),
        data=apply_placeholders(context, context.text or "{}"),
        headers=headers,
    )


@then('we get spiked content "{item_id}"')
def get_spiked_content(context, item_id):
    item_id = apply_placeholders(context, item_id)
    url = "archive/{0}".format(item_id)
    when_we_get_url(context, url)
    assert_200(context.response)
    response_data = json.loads(context.response.get_data())
    assert_equal(response_data["state"], "spiked")
    assert_equal(response_data["operation"], "spike")


@then('we get unspiked content "{id}"')
def get_unspiked_content(context, id):
    text = context.text
    context.text = ""
    url = "archive/{0}".format(id)
    when_we_get_url(context, url)
    assert_200(context.response)
    response_data = json.loads(context.response.get_data())
    assert_equal(response_data["state"], "draft")
    assert_equal(response_data["operation"], "unspike")
    # Tolga Akin (05/11/14)
    # Expiry value doesn't get set to None properly in Elastic.
    # Discussed with Petr so we'll look into this later
    # assert_equal(response_data['expiry'], None)
    if text:
        assert json_match(json.loads(apply_placeholders(context, text)), response_data)


@then("we get global content expiry")
def get_global_content_expiry(context):
    validate_expired_content(context, context.app.config["CONTENT_EXPIRY_MINUTES"], utcnow())


@then("we get content expiry {minutes}")
def get_content_expiry(context, minutes):
    validate_expired_content(context, minutes, utcnow())


@then('we get expiry for schedule and embargo content {minutes} minutes after "{future_date}"')
def get_content_expiry_schedule(context, minutes, future_date):
    future_date = parse_date(apply_placeholders(context, future_date))
    validate_expired_content(context, minutes, future_date)


@then('we get desk spike expiry after "{test_minutes}"')
def get_desk_spike_expiry(context, test_minutes):
    validate_expired_content(context, test_minutes, utcnow())


def validate_expired_content(context, minutes, start_datetime):
    response_data = json.loads(context.response.get_data())
    assert response_data["expiry"]
    response_expiry = parse_date(response_data["expiry"])
    expiry = start_datetime + timedelta(minutes=int(minutes))
    assert response_expiry <= expiry


@when('we mention user in comment for "{url}"')
def we_mention_user_in_comment(context, url):
    with context.app.mail.record_messages() as outbox:
        step_impl_when_post_url(context, url)
        assert len(outbox) == 1
        assert_equal(outbox[0].subject, "You were mentioned in a comment by test_user")
        email_text = outbox[0].body
        assert email_text


@when('we change user status to "{status}" using "{url}"')
def we_change_user_status(context, status, url):
    with context.app.mail.record_messages() as outbox:
        step_impl_when_patch_url(context, url)
        assert_200(context.response)
        assert len(outbox) == 1, f"there are {len(outbox)} messages"
        assert_equal(outbox[0].subject, "Your Superdesk account is " + status)
        assert outbox[0].body


@when("we get the default incoming stage")
def we_get_default_incoming_stage(context):
    data = json.loads(context.response.get_data())
    incoming_stage = data["_items"][0]["incoming_stage"] if "_items" in data else data["incoming_stage"]
    assert incoming_stage
    url = "stages/{0}".format(incoming_stage)
    when_we_get_url(context, url)
    assert_200(context.response)
    data = json.loads(context.response.get_data())
    assert data["default_incoming"] is True
    assert data["name"] == "Incoming Stage"


@then("we get stage filled in to default_incoming")
def we_get_stage_filled_in(context):
    data = json.loads(context.response.get_data())
    assert data["task"]["stage"]


@then("we get null stage")
def we_get_null_stage(context):
    data = json.loads(context.response.get_data())
    assert data["task"].get("stage", None) is None


@given('we have sessions "{url}"')
def we_have_sessions_get_id(context, url):
    when_we_get_url(context, url)
    item = json.loads(context.response.get_data())
    context.session_id = item["_items"][0]["_id"]
    context.data = item
    set_placeholder(context, "SESSION_ID", item["_items"][0]["_id"])
    setattr(context, "users", item["_items"][0]["user"])


@then("we get session by id")
def we_get_session_by_id(context):
    url = "sessions/" + context.session_id
    when_we_get_url(context, url)
    item = json.loads(context.response.get_data())
    returned_id = item["_id"]
    assert context.session_id == returned_id


@then("we delete session by id")
def we_delete_session_by_id(context):
    url = "sessions/" + context.session_id
    step_impl_when_delete_url(context, url)
    assert_200(context.response)


@when("we create a new user")
def step_create_a_user(context):
    data = apply_placeholders(context, context.text)
    with context.app.mail.record_messages() as outbox:
        context.response = context.client.post(
            get_prefixed_url(context.app, "/users"), data=data, headers=context.headers
        )
        expect_status_in(context.response, (200, 201))
        assert len(outbox) == 1
        context.email = outbox[0]


@then("we get activation email")
def step_get_activation_email(context):
    assert context.email.subject == "Superdesk account created"
    email_text = context.email.body
    words = email_text.split()
    url = urlparse(words[words.index("to") + 1])
    token = url.fragment.split("token=")[-1]
    assert token


@then("we set elastic limit")
def step_set_limit(context):
    context.app.settings["MAX_SEARCH_DEPTH"] = 1


@when("we reset elastic limit")
def step_reset_limit(context):
    context.app.settings["MAX_SEARCH_DEPTH"] = -1


@then("we get emails")
def step_we_get_email(context):
    data = json.loads(context.text)
    for email in data:
        assert check_if_email_sent(context, email)


@then("we get {count} emails")
def step_we_get_no_email(context, count):
    assert len(context.outbox) == int(count)
    if context.text:
        step_we_get_email(context)


def check_if_email_sent(context, spec):
    if context.outbox:
        for key in spec:
            found = False
            values = [getattr(email, key) for email in context.outbox]
            for value in values:
                if spec[key] in value:
                    found = True
            if not found:
                print("%s:%s not found in %s" % (key, spec[key], json.dumps(values, indent=2)))
                return False
        return True
    print("no email sent")
    return False


@then("we get activity")
def then_we_get_activity(context):
    url = apply_placeholders(context, '/activity?where={"name": {"$in": ["notify", "user:mention" , "desk:mention"]}}')
    context.response = context.client.get(get_prefixed_url(context.app, url), headers=context.headers)
    if context.response.status_code == 200:
        expect_json_length(context.response, 1, path="_items")
        item = json.loads(context.response.get_data())
        item = item["_items"][0]
        if item.get("_id"):
            setattr(context, "activity", item)
            set_placeholder(context, "USERS_ID", item["user"])


def login_as(context, username, password, user_type):
    user = {
        "username": username,
        "password": password,
        "is_active": True,
        "is_enabled": True,
        "needs_activation": False,
        user_type: user_type,
    }

    if context.text:
        user.update(json.loads(context.text))

    tests.setup_auth_user(context, user)


@given('we login as user "{username}" with password "{password}" and user type "{user_type}"')
def given_we_login_as_user(context, username, password, user_type):
    login_as(context, username, password, user_type)


@when('we login as user "{username}" with password "{password}" and user type "{user_type}"')
def when_we_login_as_user(context, username, password, user_type):
    login_as(context, username, password, user_type)


def is_user_resource(resource):
    return resource in ("users", "/users")


@then("we get {no_of_stages} invisible stages")
def when_we_get_invisible_stages(context, no_of_stages):
    with context.app.test_request_context(context.app.config["URL_PREFIX"]):
        stages = get_resource_service("stages").get_stages_by_visibility(is_visible=False)
        assert len(stages) == int(no_of_stages)


@then("we get {no_of_stages} visible stages")
def when_we_get_visible_stages(context, no_of_stages):
    with context.app.test_request_context(context.app.config["URL_PREFIX"]):
        stages = get_resource_service("stages").get_stages_by_visibility(is_visible=True)
        assert len(stages) == int(no_of_stages)


@then("we get {no_of_stages} invisible stages for user")
def when_we_get_invisible_stages_for_user(context, no_of_stages):
    data = json.loads(apply_placeholders(context, context.text))
    with context.app.test_request_context(context.app.config["URL_PREFIX"]):
        stages = get_resource_service("users").get_invisible_stages(data["user"])
        assert len(stages) == int(no_of_stages)


@then('we get "{field_name}" populated')
def then_field_is_populated(context, field_name):
    resp = parse_json_response(context.response)
    assert resp[field_name].get("user", None) is not None, "item is not populated"


@then('we get "{field_name}" not populated')
def then_field_is_not_populated(context, field_name):
    resp = parse_json_response(context.response)
    assert resp.get(field_name) is None, "%s should be none, but it is %s in %s" % (field_name, resp[field_name], resp)


@then('the field "{field_name}" value is not "{field_value}"')
def then_field_value_is_not_same(context, field_name, field_value):
    resp = parse_json_response(context.response)
    assert resp[field_name] != field_value, "values are the same"


@then('we get "{field_name}" not populated in results')
def then_field_is_not_populated_in_results(context, field_name):
    resps = parse_json_response(context.response)
    for resp in resps["_items"]:
        assert resp[field_name] is None, "item is not populated"


@when('we delete content filter "{name}"')
def step_delete_content_filter(context, name):
    with context.app.test_request_context(context.app.config["URL_PREFIX"]):
        filter = get_resource_service("content_filters").find_one(req=None, name=name)
        url = "/content_filters/{}".format(filter["_id"])
        headers = if_match(context, filter.get("_etag"))
        context.response = context.client.delete(get_prefixed_url(context.app, url), headers=headers)


@when('we rewrite "{item_id}"')
def step_impl_when_rewrite(context, item_id):
    context_data = {}
    _id = apply_placeholders(context, item_id)
    if context.text:
        context_data.update(json.loads(apply_placeholders(context, context.text)))
    data = json.dumps(context_data)
    context.response = context.client.post(
        get_prefixed_url(context.app, "/archive/{}/rewrite".format(_id)), data=data, headers=context.headers
    )
    if context.response.status_code == 400:
        return

    expect_status(context.response, 201)
    resp = parse_json_response(context.response)

    set_placeholder(context, "REWRITE_OF", _id)
    set_placeholder(context, "REWRITE_ID", resp["_id"])


@then('we get "{field_name}" does not exist')
def step_field_name_does_exist(context, field_name):
    resps = parse_json_response(context.response)

    if "_items" in resps:
        for resp in resps["_items"]:
            assert field_name not in resp, "field exists"
    else:
        assert field_name not in resps, "field exists"


@then('we get "{field_name}" does exist')
def step_field_name_does_not_exist(context, field_name):
    resps = parse_json_response(context.response)
    for resp in resps["_items"]:
        assert field_name in resp, "field does not exist"


@when('we publish "{item_id}" with "{pub_type}" type and "{state}" state')
def step_impl_when_publish_url(context, item_id, pub_type, state):
    item_id = apply_placeholders(context, item_id)
    res = get_res("/archive/" + item_id, context)
    headers = if_match(context, res.get("_etag"))
    context_data = {"state": state}
    if context.text:
        data = apply_placeholders(context, context.text)
        context_data.update(json.loads(data))
    data = json.dumps(context_data)
    context.response = context.client.patch(
        get_prefixed_url(context.app, "/archive/{}/{}".format(pub_type, item_id)), data=data, headers=headers
    )
    store_placeholder(context, "archive_{}".format(pub_type))


@then('the ingest item is routed based on routing scheme and rule "{rule_name}"')
def then_ingest_item_is_routed_based_on_routing_scheme(context, rule_name):
    with context.app.test_request_context(context.app.config["URL_PREFIX"]):
        validate_routed_item(context, rule_name, True)


@then('the ingest item is routed and transformed based on routing scheme and rule "{rule_name}"')
def then_ingest_item_is_routed_transformed_based_on_routing_scheme(context, rule_name):
    with context.app.test_request_context(context.app.config["URL_PREFIX"]):
        validate_routed_item(context, rule_name, True, True)


@then('the ingest item is not routed based on routing scheme and rule "{rule_name}"')
def then_ingest_item_is_not_routed_based_on_routing_scheme(context, rule_name):
    with context.app.test_request_context(context.app.config["URL_PREFIX"]):
        validate_routed_item(context, rule_name, False)


def validate_routed_item(context, rule_name, is_routed, is_transformed=False):
    data = json.loads(apply_placeholders(context, context.text))

    def validate_rule(action, state):
        for destination in rule.get("actions", {}).get(action, []):
            query = {
                "and": [
                    {"term": {"family_id": str(data["ingest"])}},
                    {"term": {"task.desk": str(destination["desk"])}},
                    {"term": {"task.stage": str(destination["stage"])}},
                    {"term": {"state": state}},
                ]
            }
            item = get_archive_items(query) + get_published_items(query)

            if is_routed:
                assert len(item) > 0, "No routed items found for criteria: " + str(query)
                assert item[0]["family_id"] == data["ingest"]
                assert item[0]["task"]["desk"] == str(destination["desk"])
                assert item[0]["task"]["stage"] == str(destination["stage"])
                assert item[0]["state"] == state

                if is_transformed:
                    assert item[0]["abstract"] == "Abstract has been updated"

                assert_items_in_package(item[0], state, str(destination["desk"]), str(destination["stage"]))
            else:
                assert len(item) == 0

    scheme = get_resource_service("routing_schemes").find_one(_id=data["routing_scheme"], req=None)
    rule = next((rule for rule in scheme["rules"] if rule["name"].lower() == rule_name.lower()), {})
    validate_rule("fetch", "routed")
    validate_rule("publish", "published")


@when('we schedule the routing scheme "{scheme_id}"')
def when_we_schedule_the_routing_scheme(context, scheme_id):
    with context.app.test_request_context(context.app.config["URL_PREFIX"]):
        scheme_id = apply_placeholders(context, scheme_id)
        url = apply_placeholders(context, "routing_schemes/%s" % scheme_id)
        res = get_res(url, context)
        href = get_self_href(res, context)
        headers = if_match(context, res.get("_etag"))
        rule = res.get("rules")[0]
        now = utcnow()
        from apps.rules.routing_rules import Weekdays

        rule["schedule"] = {
            "day_of_week": [Weekdays.dayname(now + timedelta(days=1)), Weekdays.dayname(now + timedelta(days=2))],
            "hour_of_day_from": "16:00:00",
            "hour_of_day_to": "20:00:00",
        }

        if len(res.get("rules")) > 1:
            rule = res.get("rules")[1]
            rule["schedule"] = {"day_of_week": [Weekdays.dayname(now)]}

        context.response = context.client.patch(
            get_prefixed_url(context.app, href), data=json.dumps({"rules": res.get("rules", [])}), headers=headers
        )
        assert_200(context.response)


def get_archive_items(query):
    req = ParsedRequest()
    req.max_results = 100
    req.args = {"filter": json.dumps(query)}
    return list(get_resource_service("archive").get(lookup=None, req=req))


def get_published_items(query):
    req = ParsedRequest()
    req.max_results = 100
    req.args = {"filter": json.dumps(query)}
    return list(get_resource_service("published").get(lookup=None, req=req))


def assert_items_in_package(item, state, desk, stage):
    if item.get("groups"):
        terms = [
            {"term": {"_id": ref.get("residRef")}}
            for ref in [ref for group in item.get("groups", []) for ref in group.get("refs", []) if "residRef" in ref]
        ]

        query = {"or": terms}
        items = get_archive_items(query)
        assert len(items) == len(terms)
        for item in items:
            assert item.get("state") == state
            assert item.get("task", {}).get("desk") == desk
            assert item.get("task", {}).get("stage") == stage


@given("I logout")
def logout(context):
    we_have_sessions_get_id(context, "/sessions")
    step_impl_when_delete_url(context, "/auth_db/{}".format(context.session_id))
    assert_200(context.response)


@then('we get "{url}" and match')
def we_get_and_match(context, url):
    url = apply_placeholders(context, url)
    response_data = get_res(url, context)
    context_data = json.loads(apply_placeholders(context, context.text))
    assert_equal(json_match(context_data, response_data), True, msg=str(context_data) + "\n != \n" + str(response_data))


@then('there is no "{key}" in response')
def there_is_no_key_in_response(context, key):
    data = get_json_data(context.response)
    assert key not in data, 'key "%s" is in %s' % (key, data)


@then('there is no "{key}" in task')
def there_is_no_key_in_preferences(context, key):
    data = get_json_data(context.response)["task"]
    assert key not in data, 'key "%s" is in task' % key


@then('there is no "{key}" in data')
def there_is_no_profile_in_data(context, key):
    data = get_json_data(context.response)["_items"][0]["data"]
    assert key not in data, 'key "%s" is in data' % key


@then('broadcast "{key}" has value "{value}"')
def broadcast_key_has_value(context, key, value):
    data = get_json_data(context.response).get("broadcast", {})
    value = apply_placeholders(context, value)
    if value.lower() == "none":
        assert data[key] is None, 'key "%s" is not none and has value "%s"' % (key, data[key])
    else:
        assert data[key] == value, 'key "%s" does not have valid value "%s"' % (key, data[key])


@then('there is no "{key}" preference')
def there_is_no_preference(context, key):
    data = get_json_data(context.response)
    assert key not in data["user_preferences"], "%s is in %s" % (key, data["user_preferences"].keys())


@then('there is no "{key}" in "{namespace}" preferences')
def there_is_no_key_in_namespace_preferences(context, key, namespace):
    data = get_json_data(context.response)["user_preferences"]
    assert key not in data[namespace], 'key "%s" is in %s' % (key, data[namespace])


@then("we check if article has Embargo")
def step_impl_then_check_embargo(context):
    assert_200(context.response)
    try:
        response_data = json.loads(context.response.get_data())
    except Exception:
        fail_and_print_body(context.response, "response is not valid json")

    if response_data.get("_meta") and response_data.get("_items"):
        for item in response_data.get("_items"):
            assert_embargo(context, item)
    else:
        assert_embargo(context, response_data)


def assert_embargo(context, item):
    if not item.get("embargo"):
        fail_and_print_body(context, context.response, "Embargo not found")


@when('embargo lapses for "{item_id}"')
def embargo_lapses(context, item_id):
    item_id = apply_placeholders(context, item_id)
    item = get_res("/archive/%s" % item_id, context)

    updates = {
        "embargo": (utcnow() - timedelta(minutes=10)),
        "schedule_settings": {"utc_embargo": (utcnow() - timedelta(minutes=10))},
    }

    with context.app.test_request_context(context.app.config["URL_PREFIX"]):
        get_resource_service("archive").system_update(id=item["_id"], original=item, updates=updates)


@then("we validate the published item expiry to be after publish expiry set in desk settings {publish_expiry_in_desk}")
def validate_published_item_expiry(context, publish_expiry_in_desk):
    assert_200(context.response)
    try:
        response_data = json.loads(context.response.get_data())
    except Exception:
        fail_and_print_body(context.response, "response is not valid json")

    if response_data.get("_meta") and response_data.get("_items"):
        for item in response_data.get("_items"):
            assert_expiry(item, publish_expiry_in_desk)
    else:
        assert_expiry(response_data, publish_expiry_in_desk)


@then('we get updated timestamp "{field}"')
def step_we_get_updated_timestamp(context, field):
    data = get_json_data(context.response)
    timestamp = arrow.get(data[field])
    now = utcnow()
    assert timestamp + timedelta(seconds=5) > now, "timestamp < now (%s, %s)" % (timestamp, now)  # 5s tolerance


def assert_expiry(item, publish_expiry_in_desk):
    embargo = item.get("embargo")
    actual = parse_date(item.get("expiry"))
    error_message = "Published Item Expiry validation fails"
    publish_expiry_in_desk = int(publish_expiry_in_desk)

    if embargo:
        expected = get_expiry_date(
            minutes=publish_expiry_in_desk, offset=datetime.strptime(embargo, "%Y-%m-%dT%H:%M:%S%z")
        )
        if actual != expected:
            raise WooperAssertionError("{}. Expected: {}, Actual: {}".format(error_message, expected, actual))
    else:
        expected = get_expiry_date(minutes=publish_expiry_in_desk)
        if expected < actual:
            raise WooperAssertionError("{}. Expected: {}, Actual: {}".format(error_message, expected, actual))


@when("run import legal publish queue")
def run_import_legal_publish_queue(context):
    with context.app.test_request_context(context.app.config["URL_PREFIX"]):
        from apps.legal_archive import ImportLegalPublishQueueCommand

        ImportLegalPublishQueueCommand().run()


@when("we expire items")
def expire_content(context):
    with context.app.test_request_context(context.app.config["URL_PREFIX"]):
        ids = json.loads(apply_placeholders(context, context.text))
        expiry = utcnow() - timedelta(minutes=5)
        for item_id in ids:
            original = get_resource_service("archive").find_one(req=None, _id=item_id)
            get_resource_service("archive").system_update(item_id, {"expiry": expiry}, original)
            get_resource_service("published").update_published_items(item_id, "expiry", expiry)

        from apps.archive.commands import RemoveExpiredContent

        RemoveExpiredContent().run()


@when("the publish schedule lapses")
def run_overdue_schedule_jobs(context):
    with context.app.test_request_context(context.app.config["URL_PREFIX"]):
        ids = json.loads(apply_placeholders(context, context.text))
        lapse_time = utcnow() - timedelta(minutes=5)
        updates = {
            "publish_schedule": lapse_time,
            "schedule_settings": {"utc_publish_schedule": lapse_time, "time_zone": None},
        }

        for item_id in ids:
            original = get_resource_service("archive").find_one(req=None, _id=item_id)
            get_resource_service("archive").system_update(item_id, updates, original)
            get_resource_service("published").update_published_items(item_id, "publish_schedule", lapse_time)
            get_resource_service("published").update_published_items(
                item_id, "schedule_settings.utc_publish_schedule", lapse_time
            )


@when("we transmit items")
def transmit_items(context):
    with context.app.test_request_context(context.app.config["URL_PREFIX"]):
        from superdesk.publish.publish_content import PublishContent

        PublishContent().run()


@when('we remove item "{_id}" from mongo')
def remove_item_from_mongo(context, _id):
    with context.app.app_context():
        context.app.data.mongo.remove("archive", {"_id": _id})


@then('we get text "{text}" in response field "{field}"')
def we_get_text_in_field(context, text, field):
    with context.app.test_request_context(context.app.config["URL_PREFIX"]):
        resp = parse_json_response(context.response)
        assert field in resp, "Field {} not found in response.".format(field)
        assert isinstance(resp.get(field), str), "Invalid type"
        assert text in resp.get(field, ""), "{} contains text: {}. Text To find: {}".format(
            field, resp.get(field, ""), text
        )


@then("we reset priority flag for updated articles")
def we_get_reset_default_priority_for_updated_articles(context):
    context.app.config["RESET_PRIORITY_VALUE_FOR_UPDATE_ARTICLES"] = True


@then("we mark the items not moved to legal")
def we_mark_the_items_not_moved_to_legal(context):
    with context.app.test_request_context(context.app.config["URL_PREFIX"]):
        ids = json.loads(apply_placeholders(context, context.text))
        for item_id in ids:
            get_resource_service("published").update_published_items(item_id, "moved_to_legal", False)


@when("we run import legal archive command")
def we_run_import_legal_archive_command(context):
    with context.app.test_request_context(context.app.config["URL_PREFIX"]):
        from apps.legal_archive.commands import ImportLegalArchiveCommand

        ImportLegalArchiveCommand().run()


@then('we find no reference of package "{reference}" in item')
def we_find_no_reference_of_package_in_item(context, reference):
    with context.app.test_request_context(context.app.config["URL_PREFIX"]):
        reference = apply_placeholders(context, reference)
        resp = parse_json_response(context.response)
        linked_in_packages = resp.get("linked_in_packages", [])
        assert reference not in [
            p.get("package") for p in linked_in_packages
        ], "Package reference {} found in item".format(reference)


@then('we set spike exipry "{expiry}"')
def we_set_spike_exipry(context, expiry):
    context.app.settings["SPIKE_EXPIRY_MINUTES"] = int(expiry)


@then("we set published item expiry {expiry}")
def we_set_published_item_expiry(context, expiry):
    context.app.settings["PUBLISHED_CONTENT_EXPIRY_MINUTES"] = int(expiry)


@then("we set copy metadata from parent flag")
def we_set_copy_metadata_from_parent(context):
    context.app.settings["COPY_METADATA_FROM_PARENT"] = True


@then('we assert the content api item "{item_id}" is published to subscriber "{subscriber}"')
def we_assert_content_api_item_is_published_to_subscriber(context, item_id, subscriber):
    with context.app.test_request_context(context.app.config["URL_PREFIX"]):
        item_id = apply_placeholders(context, item_id)
        subscriber = apply_placeholders(context, subscriber)
        req = ParsedRequest()
        req.projection = json.dumps({"subscribers": 1})
        cursor = get_resource_service("items").get_from_mongo(req, {"_id": item_id})
        assert cursor.count() > 0, "Item not found"
        item = cursor[0]
        subscriber = apply_placeholders(context, subscriber)
        assert len(item.get("subscribers", [])) > 0, "No subscribers found."
        assert subscriber in item.get("subscribers", []), "Subscriber with Id: {} not found.".format(subscriber)


@then('we assert the content api item "{item_id}" is not published to subscriber "{subscriber}"')
def we_assert_content_api_item_is_not_published_to_subscriber(context, item_id, subscriber):
    with context.app.test_request_context(context.app.config["URL_PREFIX"]):
        item_id = apply_placeholders(context, item_id)
        subscriber = apply_placeholders(context, subscriber)
        req = ParsedRequest()
        req.projection = json.dumps({"subscribers": 1})
        cursor = get_resource_service("items").get_from_mongo(req, {"_id": item_id})
        assert cursor.count() > 0, "Item not found"
        item = cursor[0]
        subscriber = apply_placeholders(context, subscriber)
        assert subscriber not in item.get("subscribers", []), "Subscriber with Id: {} found for the item. ".format(
            subscriber
        )


@then('we assert the content api item "{item_id}" is not published to any subscribers')
def we_assert_content_api_item_is_not_published(context, item_id):
    with context.app.test_request_context(context.app.config["URL_PREFIX"]):
        item_id = apply_placeholders(context, item_id)
        req = ParsedRequest()
        req.projection = json.dumps({"subscribers": 1})
        cursor = get_resource_service("items").get_from_mongo(req, {"_id": item_id})
        assert cursor.count() > 0, "Item not found"
        item = cursor[0]
        assert len(item.get("subscribers", [])) == 0, "Item published to subscribers {}.".format(
            item.get("subscribers", [])
        )


@then("we ensure that archived schema extra fields are not present in duplicated item")
def we_ensure_that_archived_schema_extra_fields_are_not_present(context):
    with context.app.test_request_context(context.app.config["URL_PREFIX"]):
        eve_keys = set([config.ID_FIELD, config.LAST_UPDATED, config.DATE_CREATED, config.VERSION, config.ETAG])
        archived_schema_keys = set(context.app.config["DOMAIN"]["archived"]["schema"].keys()).union(eve_keys)
        archive_schema_keys = set(context.app.config["DOMAIN"]["archive"]["schema"].keys()).union(eve_keys)
        extra_fields = [key for key in archived_schema_keys if key not in archive_schema_keys]
        duplicate_item = json.loads(context.response.get_data())
        for field in extra_fields:
            assert field not in duplicate_item, "Field {} found the duplicate item".format(field)


@then('we assert content api item "{item_id}" with associated item "{embedded_id}" is published to "{subscriber}"')
def we_assert_that_associated_item_for_subscriber(context, item_id, embedded_id, subscriber):
    with context.app.test_request_context(context.app.config["URL_PREFIX"]):
        item_id = apply_placeholders(context, item_id)
        subscriber = apply_placeholders(context, subscriber)
        embedded_id = apply_placeholders(context, embedded_id)
        req = ParsedRequest()
        cursor = get_resource_service("items").get_from_mongo(req, {"_id": item_id})
        assert cursor.count() > 0, "Item not found"
        item = cursor[0]
        assert embedded_id in (item.get("associations") or {}), "{} association not found.".format(embedded_id)
        assert subscriber in (item["associations"][embedded_id] or {}).get(
            "subscribers", []
        ), "{} subscriber not found in associations {}".format(subscriber, embedded_id)


@then('we assert content api item "{item_id}" with associated item "{embedded_id}" is not published to "{subscriber}"')
def we_assert_content_api_not_published(context, item_id, embedded_id, subscriber):
    with context.app.test_request_context(context.app.config["URL_PREFIX"]):
        item_id = apply_placeholders(context, item_id)
        subscriber = apply_placeholders(context, subscriber)
        embedded_id = apply_placeholders(context, embedded_id)
        req = ParsedRequest()
        cursor = get_resource_service("items").get_from_mongo(req, {"_id": item_id})
        assert cursor.count() > 0, "Item not found"
        item = cursor[0]
        assert embedded_id in (item.get("associations") or {}), "{} association not found.".format(embedded_id)
        assert subscriber not in (item["associations"][embedded_id] or {}).get(
            "subscribers", []
        ), "{} subscriber found in associations {}".format(subscriber, embedded_id)


@then('file exists "{path}"')
def then_file_exists(context, path):
    assert os.path.isfile(path), "{} is not a file".format(path)


@then("we get package items")
def then_we_get_package_item(context):
    package = json.loads(context.response.get_data())
    items = []
    for group in package.get("groups", []):
        for ref in group.get("refs", []):
            if ref.get("residRef"):
                url = get_prefixed_url(context.app, "%s/%s" % (ref.get("location", "archive"), ref["residRef"]))
                response = context.client.get(url, headers=context.headers)
                assert response.status_code == 200, response.status_code
                items.append(json.loads(response.get_data()))
    context_items = json.loads(context.text)
    test_items_contain_items(items, context_items)


@then('we store "{tag}" with first item')
def step_impl_store_first_item_to_ctx(context, tag):
    data = get_json_data(context.response)
    first_item = data["_items"][0]
    setattr(context, tag, first_item)


@then('we store "{tag}" with {index} item')
def step_impl_store_indexed_item_to_ctx(context, tag, index):
    data = get_json_data(context.response)
    item = data["_items"][int(index) - 1]
    setattr(context, tag, item)


@then('we store response in "{tag}"')
def step_impl_store_response_in_cts(context, tag):
    data = get_json_data(context.response)
    setattr(context, tag, data)


def test_items_contain_items(items, context_items):
    for context_item in context_items:
        for item in items:
            if context_item.items() <= item.items():
                break
        else:
            assert False, "missing item = %s" % json.dumps(context_item, indent=2)
    return True


@then("we get desk members count as {count}")
def step_impl_we_get_desk_members_count(context, count):
    desk = get_json_data(context.response) or {}
    assert len(desk.get("members") or []) == int(count), "Invalid desk members"


@when('we register custom schema field "{name}"')
def when_register_custom_schema_field(context, name):
    superdesk.register_item_schema_field(name, schema=json.loads(context.text), app=context.app)


# Auth Server


@given("authorized clients")
def step_impl_given_authorized_client(context):
    from superdesk.auth_server import clients

    clients_data = json.loads(context.text)
    with context.app.app_context():
        for client_data in clients_data:
            clients.RegisterClient().run(**client_data)


@when('we do OAuth2 client authentication with id "{client_id}" and password "{password}"')
def step_impl_when_oauth2_client_auth(context, client_id, password):
    from superdesk.auth_server.oauth2 import TOKEN_ENDPOINT

    encoded_user_pass = b64encode(b"%s:%s" % (client_id.encode(), password.encode())).decode("ascii")
    headers = [
        ("Content-Type", "multipart/form-data"),
        ("Authorization", "Basic {}".format(encoded_user_pass)),
    ]
    headers = unique_headers(headers, context.headers)
    context.response = context.client.post(
        get_prefixed_url(context.app, TOKEN_ENDPOINT), data={"grant_type": "client_credentials"}, headers=headers
    )


@then("we get a valid access token")
def step_impl_then_we_get_access_token(context):
    assert context.response.status_code == 200
    resp = json.loads(context.response.data)
    assert set(resp).issuperset({"expires_in", "token_type", "access_token"})
    # we now validate JWT signature and payload

    # we first try to decode with a bad secret, it must fail
    try:
        jwt.decode(resp["access_token"], "BAD_SECRET")
    except BadSignatureError:
        pass
    else:
        raise Exception("jwt.decode should raise an error with wrong secret")

    # and now we try with the right secret, it should work this time
    claims = jwt.decode(resp["access_token"], context.app.config["AUTH_SERVER_SHARED_SECRET"])

    # we validate the payload
    claims.validate()

    # and check that we get expected keys
    assert set(claims).issuperset({"client_id", "iss", "iat", "exp", "scope"})


@then("we don't get an access token")
def step_impl_then_we_dont_get_access_token(context):
    resp = json.loads(context.response.data)
    assert context.response.status_code == 401
    assert resp == {"error": "invalid_client"}


@when('we init data "{entity}"')
def setp_impl_when_we_init_data(context, entity):
    with context.app.app_context():
        AppInitializeWithDataCommand().run(entity)


@when('we run task "{name}"')
def when_we_run_task(context, name):
    task = celery.signature(name)
    assert task is not None
    task.apply()


@when('the lock expires "{url}"')
def when_lock_expires(context, url):
    url = apply_placeholders(context, url).encode("ascii").decode("unicode-escape")
    resource, _id = url.lstrip("/").rstrip("/").split("/")
    with context.app.app_context():
        orig = context.app.data.find_one(resource, req=None, _id=_id)
        assert orig is not None, "could not find {}/{}".format(resource, _id)
        context.app.data.update(resource, orig["_id"], {"_lock_time": utcnow() - timedelta(hours=48)}, orig)


@then('we get picture metadata "{media}"')
def then_we_get_picture_metadta(context, media):
    with context.app.app_context():
        media = render_template_string(media, **getattr(context, "placeholders", {}))
        binary = context.app.media.get(media)
        assert binary, "Binary for media id {} not found".format(media)
        metadata = read_metadata(binary.read())
    context_data = json.loads(apply_placeholders(context, context.text))
    assert json_match(context_data, metadata), str(context_data) + "\n != \n" + str(metadata)
