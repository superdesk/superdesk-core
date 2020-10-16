from string import Template


def process_common_templates(text, context):
    template = Template(text)
    result_text = text
    for key, value in context.template_variables.items():
        result_text = template.substitute({key: value})
    return result_text


def first_row_to_dict(table):
    if not table:
        return None
    return {key: table[0][key] for key in table.headings}


def get_context_input(context):
    return first_row_to_dict(getattr(context, 'table')) \
        or process_common_templates(context.text, context)
