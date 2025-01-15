from uuid import uuid4


def generate_index_name(alias: str):
    random = str(uuid4()).split("-")[0]
    return "{}_{}".format(alias, random)
