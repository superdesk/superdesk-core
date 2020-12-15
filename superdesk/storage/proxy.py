import logging

from typing import List

from . import SuperdeskMediaStorage
from .desk_media_storage import SuperdeskGridFSMediaStorage
from .amazon_media_storage import AmazonMediaStorage


logger = logging.getLogger(__name__)


def log_missing_media(id_or_filename, resource=None):
    logger.error(
        "Media item not found",
        extra=dict(
            id=id_or_filename,
            resource=resource,
        ),
    )


class MissingMediaError(ValueError):
    pass


class ProxyMediaStorage(SuperdeskMediaStorage):

    _storage: List[SuperdeskMediaStorage]

    def __init__(self, app):
        super().__init__(app)

        self._storage = [SuperdeskGridFSMediaStorage(app)]

        if app.config.get("AMAZON_CONTAINER_NAME"):
            # make amazon first if configured, so it will be the default
            self._storage.insert(0, AmazonMediaStorage(app))

    def storage(self, id_or_filename=None, resource=None, fallback=False) -> SuperdeskMediaStorage:
        if id_or_filename:
            for storage in self._storage:
                if storage.exists(id_or_filename, resource):
                    logger.debug("got media from storage id=%s storage=%s", id_or_filename, storage)
                    return storage
            if not fallback:
                log_missing_media(id_or_filename, resource)
                raise MissingMediaError

        return self._storage[0]

    def get(self, id_or_filename, resource=None):
        try:
            return self.storage(id_or_filename, resource).get(id_or_filename, resource=resource)
        except MissingMediaError:
            return

    def delete(self, id_or_filename, resource=None):
        try:
            return self.storage(id_or_filename, resource).delete(id_or_filename, resource=resource)
        except MissingMediaError:
            return True

    def exists(self, id_or_filename, resource=None):
        try:
            return self.storage(id_or_filename, resource).exists(id_or_filename, resource=resource)
        except MissingMediaError:
            return False

    def put(self, content, filename=None, content_type=None, metadata=None, resource=None, **kwargs):
        return self.storage(None, resource).put(
            content, filename=filename, content_type=content_type, metadata=metadata, resource=resource, **kwargs
        )

    def url_for_media(self, media_id, content_type=None):
        return self.storage(media_id, fallback=True).url_for_media(media_id, content_type=content_type)

    def url_for_download(self, media_id, content_type=None):
        return self.storage(media_id, fallback=True).url_for_download(media_id, content_type=content_type)

    def fetch_rendition(self, rendition):
        if rendition.get("media"):
            return self.get(rendition["media"])

        for storage in self._storage:
            media = storage.fetch_rendition(rendition)
            if media:
                return media

    def get_by_filename(self, filename):
        for storage in self._storage:
            media = storage.get_by_filename(filename)
            if media:
                return media
