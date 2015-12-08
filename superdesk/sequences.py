from superdesk import get_resource_service


def get_next_sequence_number(
    resource_name, item_id,
    max_seq_number, min_seq_number=0,
    field_name='sequence_number'
):
    """
    Generates Sequence Number
    :param resource_name: target resource
    :param item_id: target item id
    :param max_seq_number: maximal possible value
    :param min_seq_number: default 0, minimal possible value
    :param field_name: default 'sequence_number', name of field to store sequence_number in the target item
    :returns: sequence_number
    """

    target_resource = get_resource_service(resource_name)
    sequence_number = target_resource.find_one(
        req=None,
        _id=item_id
    ).get(field_name) or min_seq_number
    if (min_seq_number <= sequence_number + 1 <= max_seq_number):
        target_resource.find_and_modify(
            query={'_id': item_id},
            update={'$inc': {field_name: 1}},
            upsert=False
        )
    else:
        target_resource.find_and_modify(
            query={'_id': item_id},
            update={field_name: min_seq_number},
            upsert=False
        )

    return sequence_number
