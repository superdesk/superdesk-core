# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015, 2016 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


import requests_mock
from flask import json
from behave import when, then  # @UnresolvedImport
from apps.publish.enqueue import enqueue_published
from superdesk.tests.steps import assert_200, apply_placeholders, json_match, get_json_data, test_json, format_items
from wooper.general import fail_and_print_body
from wooper.assertions import assert_equal
from superdesk.publish import transmit


@when("we enqueue published")
def step_impl_when_auth(context):
    enqueue_published.apply_async()


@then("we get formatted item")
def then_we_get_formatted_item(context):
    assert_200(context.response)
    try:
        response_data = json.loads(context.response.get_data())
        formatted_item = json.loads(response_data.get("formatted_item", ""))
    except Exception:
        fail_and_print_body(context.response, "response does not contain a valid formatted_item field")
    context_data = json.loads(apply_placeholders(context, context.text))
    assert_equal(
        json_match(context_data, formatted_item), True, msg=str(context_data) + "\n != \n" + str(formatted_item)
    )


@then("we get {total_count} queued items")
def then_we_get_formatted_items(context, total_count):
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
        test_json(context, ["formatted_item"])


@then("we pushed 1 item")
def then_we_pushed_1_item(context):
    return then_we_pushed_x_items(context, 1)


@then("we pushed {count} items")
def then_we_pushed_x_items(context, count):
    history = context.http_mock.request_history
    assert count == len(history), "there were %d calls" % (len(history),)
    if context.text:
        context_data = json.loads(apply_placeholders(context, context.text))
        for i, _ in enumerate(context_data):
            assert_equal(json_match(context_data[i], history[i].json()), True, msg="item[%d]: %s" % (i, history[i]))


@when("we transmit published")
def when_we_transmit_published(context):
    with requests_mock.Mocker() as m:
        context.http_mock = m
        m.post("mock://publish", text=json.dumps({}))
        m.post("mock://assets", text=json.dumps({}))
        transmit.apply_async()
        transmit.apply_async()
