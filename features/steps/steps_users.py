from behave import then
from behave.api.async_step import async_run_until_complete
from superdesk.core import json


@then("we get users")
@async_run_until_complete
async def then_we_get_users(context):
    usernames = json.loads(context.text)
    response_users = json.loads(await context.response.get_data())["_items"]
    for i in range(len(usernames)):
        username = usernames[i]
        response_username = response_users[i]["username"]
        assert username == response_username, "user #{} should be {}, but it was {}".format(
            i, username, response_username
        )
