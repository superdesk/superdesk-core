from behave import given

from .. import rest


@given('using last id')
def step_imp_use_last_id(context):
    context.template_variables['last_id'] = rest.get_id_from_href(context)
