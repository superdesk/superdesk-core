from flask import json


def set_filemeta(item, metadata):
    """Set filemeta info into item for storage.

    it's json encoded so it can be stored into elastic without mapping

    :param item: news item dict
    :param metadata: metadata dict
    """
    item["filemeta_json"] = json.dumps(metadata)


def get_filemeta(item, key=None, default_value=None):
    """Get file metadata.

    :param item: news item dict
    :param key: key string
    :param default_value
    """
    if item.get("filemeta_json"):
        meta = json.loads(item["filemeta_json"])
    else:
        meta = item.get("filemeta", {})

    return meta.get(key, default_value) if key else meta
