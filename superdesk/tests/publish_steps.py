# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015, 2016 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


from flask import json
from behave import when, then  # @UnresolvedImport
from apps.publish.enqueue import enqueue_published
from superdesk.tests.steps import assert_200, apply_placeholders, json_match
from wooper.general import fail_and_print_body
from wooper.assertions import assert_equal


@when('we enqueue published')
def step_impl_when_auth(context):
    enqueue_published.apply_async()


@then('we get formatted item')
def then_we_get_formatted_item(context):
    assert_200(context.response)
    try:
        response_data = json.loads(context.response.get_data())
        formatted_item = json.loads(response_data.get('formatted_item', ''))
    except Exception:
        fail_and_print_body(context.response, 'response does not contain a valid formatted_item field')
    context_data = json.loads(apply_placeholders(context, context.text))
    assert_equal(json_match(context_data, formatted_item), True,
                 msg=str(context_data) + '\n != \n' + str(formatted_item))
