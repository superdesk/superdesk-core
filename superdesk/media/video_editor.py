import socket
import logging
from urllib.parse import urljoin
from flask import current_app as app
from superdesk.errors import SuperdeskApiError

import requests
from bson import json_util
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class VideoEditorFactory():
    """Base class for Video Editor.
    """

    def get(self, project_id):
        """Get single project.

        :param project_id:
        """
        raise NotImplementedError

    def get_paginate(self, page):
        """Get list of projects.

        :param page:
        """
        raise NotImplementedError

    def post(self, file_storage):
        """Create new project.

        :param file_storage:
        """
        raise NotImplementedError

    def duplicate(self, project_id):
        """Duplicate video. This method clone original project and increase version.

        :param project_id: id project.
        :param updates: changes apply to the video.
        """
        raise NotImplementedError

    def put(self, project_id, updates):
        """Edit video. This method does not create a new project.

        :param project_id: id project.
        :param updates: changes apply to the video.
        """
        raise NotImplementedError

    def delete(self, project_id):
        """Delete video in video server.

        :param project_id:
        """
        raise NotImplementedError

    def get_timeline_thumbnails(self, project_id, amount):
        """Get video thumbnails.

        :param project_id:
        :param amount: number of thumbnails to generate/get
        """
        raise NotImplementedError

    def post_preview_thumbnail(self, project_id, file):
        """Upload video preview thumbnail to video server.

        :param project_id:
        :param post_type: Post preview thumbnail type, either capture or upload
        :param time: time to capture
        :param base64_data: base64 image data if type is upload
        """
        raise NotImplementedError

    def get_preview_thumbnail(self, project_id, position=0, crop=None, rotate=None):
        """Capture thumbnail of video on video-server.

        :param project_id:
        :param time: period time to capture the image in video
        :return:
        """
        raise NotImplementedError

    def check_video_server(self):
        """Check the video-server is exist."""
        raise NotImplementedError


class VideoEditorService(VideoEditorFactory):
    """Video Service for integating with video server"""

    label = 'Video Editor'

    def __init__(self, ):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'superdesk'})

    def get_base_url(self):
        return app.config.get('VIDEO_SERVER_URL') + '/projects/'

    def check_video_server(self):
        parse = urlparse(app.config.get('VIDEO_SERVER_URL'))
        host = parse.hostname
        port = parse.port if parse.port else 80
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex((host, port))
        if result == 0:
            return True
        else:
            return False

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

    def get(self, project_id):
        try:
            resp = self.session.get(self._url(project_id))
            return self._get_response(resp, 200)
        except ConnectionError as ex:
            raise SuperdeskApiError(message=ex.args[0], status_code=500)

    def get_paginate(self, page):
        try:
            resp = self.session.get(self.get_base_url(), params={'page': page})
            return self._get_response(resp, 200)
        except ConnectionError as ex:
            raise SuperdeskApiError(message=ex.args[0], status_code=500)

    def post(self, file_storage):
        try:
            video_file = {'file': (file_storage.filename, file_storage.read(), file_storage.mimetype)}
            resp = self.session.post(self.get_base_url(), files=video_file)
            return self._get_response(resp, 201)
        except ConnectionError as ex:
            raise SuperdeskApiError(message=ex.args[0], status_code=500)

    def duplicate(self, project_id):
        try:
            resp = self.session.post(self._url(project_id, "duplicate"))
            return self._get_response(resp, 201)
        except ConnectionError as ex:
            raise SuperdeskApiError(message=ex.args[0], status_code=500)

    def put(self, project_id, updates):
        try:
            resp = self.session.put(self._url(project_id), json=updates)
            return self._get_response(resp, 202)
        except ConnectionError as ex:
            raise SuperdeskApiError(message=ex.args[0], status_code=500)

    def delete(self, project_id):
        try:
            resp = self.session.delete(self._url(project_id))
            if resp.status_code != 204:
                logger.exception(resp.text)
                resp.raise_for_status()
            return True
        except ConnectionError as ex:
            raise SuperdeskApiError(message=ex.args[0], status_code=500)

    def get_timeline_thumbnails(self, project_id, amount):
        try:
            params = {
                'type': 'timeline',
                'amount': amount
            }
            resp = self.session.get(self._url(project_id, 'thumbnails'), params=params)
            return self._get_response(resp, 202)
        except ConnectionError as ex:
            raise SuperdeskApiError(message=ex.args[0], status_code=500)

    def post_preview_thumbnail(self, project_id, file):
        try:
            payloads = {
                'file': file,
            }
            resp = self.session.post(self._url(project_id, 'thumbnails'), json=payloads)
            return self._get_response(resp, 200)
        except ConnectionError as ex:
            raise SuperdeskApiError(message=ex.args[0], status_code=500)

    def get_preview_thumbnail(self, project_id, position=0, crop=None, rotate=None):
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
