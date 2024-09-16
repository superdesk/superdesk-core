from superdesk.core.resources import ResourceModel, ModelWithVersions


class Content(ResourceModel, ModelWithVersions):
    guid: str
    lock_user: str | None = None
    headline: str | None = None
    uri: str | None = None
