import superdesk

import logging
import superdesk
import base64
import os
import sys
from io import BytesIO
import subprocess as cmd
from flask import current_app as app, json
from superdesk.media.media_operations import get_info_file_from_stream, decode_metadata
from superdesk.utils import get_random_string


class VideoEditService(superdesk.Service):
    """Crop original image of picture item and return its url.

    It is used for embedded images within text item body.
    """

    def create(self, docs, **kwargs):
        res = {}
        for doc in docs:
            item = doc.pop('item')
            thumbnail_add = doc.pop('thumbnail_add')
            video_cut = doc.pop('video_cut')
            path_temp_file = None
            renditions = []
            try:
                if thumbnail_add or video_cut:
                    path_temp_file = self.create_temp_media(item['media'])
                if thumbnail_add:
                    rendition = self.thumbnail_add(path_temp_file, thumbnail_add)
                    renditions.append(rendition)

                if video_cut:
                    mimetype = item['renditions']['original']['mimetype']
                    rendition = self.video_cut(path_temp_file, mimetype, video_cut['starttime'],
                                              video_cut['endtime'])
                    renditions.append(rendition)

            finally:
                os.remove(path_temp_file)
                pass
            doc['result'] = renditions
        return {renditions}

    def video_cut(self, path_file, mimetype, start_time, end_time):
        try:
            path_output = path_file + "_cut." + str.split(mimetype, "/")[1]
            content = self._cutting_video(path_file, path_output, start_time, end_time)
            res = get_info_file_from_stream(content, content_type=mimetype)
            file_name, content_type, metadata, content = res
            media_id = app.media.put(content, filename=file_name, content_type=content_type,
                                 metadata=metadata)
            rendition = {
                'original': {
                    'href': app.media.url_for_media(media_id, mimetype),
                    'media': media_id,
                    'mimetype': mimetype
                }
            }
            return rendition
        finally:
            os.remove(path_output)

    def thumbnail_add(self, path_input, thumbnail_add):
        mimetype = None
        content = None
        if thumbnail_add['type'] == 'capture':
            mimetype = "image/png"
            path_output = path_input + "_thumnail.png"
            try:
                content = self._capture_thumnail(path_input, path_output, thumbnail_add['time'])
            finally:
                os.remove(path_output)
        if thumbnail_add['type'] == 'upload':
            header, data = str.split(thumbnail_add['data'], ',')
            mimetype = header.split(";")[0].split(":")[1]
            content = BytesIO(base64.b64decode(data))
        res = get_info_file_from_stream(content, content_type=mimetype)
        file_name, content_type, metadata, content = res
        media_id = app.media.put(content, file_name, content_type, metadata=metadata)
        rendition = {
            'thumbnail': {
                'href': app.media.url_for_media(media_id, mimetype),
                'media': media_id,
                'mimetype': mimetype
            }
        }
        return rendition

    def create_temp_media(self, media_id):
        media_id = app.media.getFilename(media_id)
        media_file = app.media.get(media_id, 'upload')
        tmp_path = "/tmp/tmp_%s" % media_id
        with open(tmp_path, "wb") as f:
            f.write(media_file.read())
        return tmp_path

    def _capture_thumnail(self, path_video, path_output, time_capture=0):
        cmd.run(["ffmpeg", "-i", path_video, "-ss", str(time_capture), "-vframes", "1", path_output])
        return BytesIO(open(path_output, "rb+").read())

    def _cutting_video(self, path_video, path_output, start_time, end_time):
        cmd.run(["ffmpeg", "-i", path_video, "-ss", str(start_time), "-t", str(end_time), "-strict", "-2",
                 path_output])
        return BytesIO(open(path_output, "rb+").read())

    def get(self, req, lookup):
        test = 'hello'

    pass


class VideoEditResource(superdesk.Resource):
    item_methods = []
    resource_methods = ['POST']
    privileges = {'POST': 'archive'}

    schema = {
        'item': {'type': 'dict', 'required': True, 'empty': False},
        'thumbnail_add': {'type': 'dict', 'required': True, 'empty': True},
        'video_cut': {'type': 'dict', 'required': True, 'empty': True}
    }


def init_app(app):
    superdesk.register_resource(
        'video_edit',
        VideoEditResource,
        VideoEditService,
        'archive')
