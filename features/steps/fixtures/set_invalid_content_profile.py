def set_invalid_content_profile(item, **kwargs):
    item["profile"] = "foo_bar_gone"
    return item


name = "set_invalid_profile_id"
label = "Set invalid content profile"
callback = set_invalid_content_profile
access_type = "backend"
action_type = "direct"
