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

    label = 'unknown'

    def __init__(self, provider):
        self.provider = provider

    def get(self, project_id):
        """Get single project.

        :param project_id:
        """
        raise NotImplementedError

    def get_paginate(self, offset):
        """Get list of projects.

        :param offset:
        """
        raise NotImplementedError

    def post_project(self, filestream):
        """Create new project.

        :param filestream:
        """
        raise NotImplementedError

    def post(self, project_id, updates):
        """Edit video. This method creates a new project.

        :param project_id:
        :param updates: changes apply to the video
        """
        raise NotImplementedError

    def put(self, project_id, updates):
        """Edit video. This method does not create a new project.

        :param project_id:
        :param updates: changes apply to the video
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

    def post_preview_thumbnail(self, project_id, post_type, time=None, base64_data=None):
        """Upload video preview thumbnail to video server.

        :param project_id:
        :param post_type: Post preview thumbnail type, either capture or upload
        :param time: time to capture
        :param base64_data: base64 image data if type is upload
        """
        raise NotImplementedError

    def get_preview_thumbnail(self, project_id, time=None):
        """Capture image from video-server.

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
        return app.config.get('VIDEO_SERVER_HOST') + '/projects/'

    def check_video_server(self):
        parse = urlparse(app.config.get('VIDEO_SERVER_HOST'))
        host = parse.hostname
        port = parse.port if parse.port else 80
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex((host, port))
        if result == 0:
            return True
        else:
            return False

    def _url(self, _id, resource=''):
        url = urljoin(self.get_base_url(), _id)
        if resource:
            return urljoin(url + '/', resource)
        return url

    def _get_response(self, resp, *status):
        json = json_util.loads(resp.text)
        if resp.status_code not in status:
            if resp.status_code == 400:
                raise SuperdeskApiError.badRequestError(message=json.get('message'))
            resp.raise_for_status()
        return json

    def get(self, project_id):
        resp = self.session.get(self._url(str(project_id)))
        return self._get_response(resp, 200)

    def get_paginate(self, offset):
        resp = self.session.get(self.get_base_url(), params={'offset': offset})
        return self._get_response(resp, 200)

    def post_project(self, file_storage):
        video_file = {'file': (file_storage.filename, file_storage.read(), file_storage.mimetype)}
        resp = self.session.post(self.get_base_url(), files=video_file)
        return self._get_response(resp, 200)

    def post(self, project_id, updates):
        resp = self.session.post(self._url(str(project_id)), json=updates)
        return self._get_response(resp, 201)

    def put(self, project_id, updates):
        resp = self.session.put(self._url(str(project_id)), json=updates)
        return self._get_response(resp, 200)

    def delete(self, project_id):
        resp = self.session.delete(self._url(str(project_id)))
        if resp.status_code != 204:
            logger.exception(resp.text)
            resp.raise_for_status()

        return True

    def get_timeline_thumbnails(self, project_id, amount):
        resp = self.session.get(self._url(str(project_id), 'thumbnails'), params={'type': 'timeline', 'amount': amount})
        return self._get_response(resp, 200)

    def post_preview_thumbnail(self, project_id, base64_data=None):
        payloads = {
            'data': base64_data,
        }
        resp = self.session.post(self._url(str(project_id), 'thumbnails'), json=payloads)

        return self._get_response(resp, 200)

    def get_preview_thumbnail(self, project_id, time=None):

        resp = self.session.get(self._url(str(project_id), 'thumbnails'), params={'type': 'preview', "time": time})
        return self._get_response(resp, 200)
