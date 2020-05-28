import logging
from urllib.parse import urljoin

import requests
from bson import json_util
from flask import current_app as app

from superdesk.errors import SuperdeskApiError

logger = logging.getLogger(__name__)


class VideoEditorWrapper():
    """Video Service for integating with video server"""

    label = 'Video Editor'

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'superdesk'})

    def get_base_url(self):
        return app.config.get('VIDEO_SERVER_URL') + '/projects/'

    def create(self, file):
        return self._post(file)

    def edit(self, _id, updates):
        project = self._get(_id)
        response = {}
        if project.get('version', 1) == 1:
            response = self._duplicate(_id)
            _id = response.get('_id', _id)
        try:
            self._put(_id, updates)
        except SuperdeskApiError as ex:
            if response:
                self._delete(_id)
            raise ex
        return self._get(_id)

    def find_one(self, _id):
        return self._get(_id)

    def capture_preview_thumbnail(self, _id, position=0, crop=None, rotate=None):
        self._get_preview_thumbnail(_id, position, crop, rotate)
        return self._get(_id)

    def upload_preview_thumbnail(self, _id, file_storage):
        return self._post_preview_thumbnail(_id, file_storage)

    def create_timeline_thumbnails(self, _id, amount):
        return self._get_timeline_thumbnails(_id, amount)

    def _url(self, _id, resource=''):
        url = urljoin(self.get_base_url(), str(_id))
        if resource:
            return urljoin(url + '/', resource)
        return url

    def _get_response(self, resp, *status):
        json = json_util.loads(resp.text)
        if resp.status_code not in status:
            if resp.status_code == 400:
                raise SuperdeskApiError.badRequestError(message=json)
            if resp.status_code == 409:
                raise SuperdeskApiError.conflictError(message=json)
            if resp.status_code == 404:
                raise SuperdeskApiError.notFoundError(message=json)
            if resp.status_code == 500:
                raise SuperdeskApiError.internalError(message=json)
        return json

    def _get(self, project_id):
        try:
            resp = self.session.get(self._url(project_id))
            return self._get_response(resp, 200)
        except ConnectionError as ex:
            raise SuperdeskApiError(message=ex.args[0], status_code=500)

    def _get_paginate(self, page):
        try:
            resp = self.session.get(self.get_base_url(), params={'page': page})
            return self._get_response(resp, 200)
        except ConnectionError as ex:
            raise SuperdeskApiError(message=ex.args[0], status_code=500)

    def _post(self, file_storage):
        try:
            video_file = {'file': (file_storage.filename, file_storage.read(), file_storage.mimetype)}
            resp = self.session.post(self.get_base_url(), files=video_file)
            return self._get_response(resp, 201)
        except ConnectionError as ex:
            raise SuperdeskApiError(message=ex.args[0], status_code=500)

    def _duplicate(self, project_id):
        try:
            resp = self.session.post(self._url(project_id, "duplicate"))
            return self._get_response(resp, 201)
        except ConnectionError as ex:
            raise SuperdeskApiError(message=ex.args[0], status_code=500)

    def _put(self, project_id, updates):
        try:
            resp = self.session.put(self._url(project_id), json=updates)
            return self._get_response(resp, 202)
        except ConnectionError as ex:
            raise SuperdeskApiError(message=ex.args[0], status_code=500)

    def _delete(self, project_id):
        try:
            resp = self.session.delete(self._url(project_id))
            if resp.status_code != 204:
                logger.exception(resp.text)
                resp.raise_for_status()
            return True
        except ConnectionError as ex:
            raise SuperdeskApiError(message=ex.args[0], status_code=500)

    def _get_timeline_thumbnails(self, project_id, amount):
        try:
            params = {
                'type': 'timeline',
                'amount': amount
            }
            resp = self.session.get(self._url(project_id, 'thumbnails'), params=params)
            return self._get_response(resp, 202)
        except ConnectionError as ex:
            raise SuperdeskApiError(message=ex.args[0], status_code=500)

    def _post_preview_thumbnail(self, project_id, file_storage):
        try:
            video_file = {'file': (file_storage.filename, file_storage.read(), file_storage.mimetype)}
            resp = self.session.post(self._url(project_id, 'thumbnails'), files=video_file)
            return self._get_response(resp, 200)
        except ConnectionError as ex:
            raise SuperdeskApiError(message=ex.args[0], status_code=500)

    def _get_preview_thumbnail(self, project_id, position=0, crop=None, rotate=None):
        try:
            params = {
                "type": "preview",
                "position": position
            }
            if crop:
                params["crop"] = crop
            if rotate:
                params["rotate"] = rotate
            resp = self.session.get(self._url(project_id, 'thumbnails'), params=params)
            return self._get_response(resp, 202)
        except ConnectionError as ex:
            raise SuperdeskApiError(message=ex.args[0], status_code=500)
