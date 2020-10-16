from behave import then

from ..expect import (
    expect_status,
    expect_json, expect_json_length,
    expect_json_contains, expect_json_not_contains,
)
from .general import get_context_input


@then('status is {status:d}')
def step_impl_status(context, status):
    expect_status(context.response, status)


@then('json is')
def step_impl_json_is(context):
    expect_json(context.response, get_context_input(context))


@then('json contains')
def step_impl_json_contains(context):
    expect_json_contains(context.response, get_context_input(context))


@then('json not contains')
def step_impl_json_not_contains(context):
    expect_json_not_contains(context.response, get_context_input(context))


@then('{path} json contains')
def step_impl_path_json_contains(context, path):
    expect_json_contains(context.response,
                         get_context_input(context), path=path)


@then('json length is {length:n}')
def step_impl_json_length(context, length):
    expect_json_length(context.response, length)


@then('{path} json length is {length:n}')
def step_impl_path_json_length(context, path, length):
    expect_json_length(context.response, length, path=path)
