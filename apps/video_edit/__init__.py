import superdesk
from apps.archive.common import ARCHIVE
from superdesk import config
from superdesk.errors import SuperdeskApiError
from superdesk.media.video_editor import VideoEditorWrapper
from superdesk.metadata.utils import item_url


class VideoEditService(superdesk.Service):
    """
    Edit video
    Use ffmpeg to create thumbnail and cutting video
    """

    videoEditor = VideoEditorWrapper()

    def create(self, docs, **kwargs):
        ids = []
        for doc in docs:
            item = doc.get('item')
            item_id = item.get(config.ID_FIELD)
            media_id = item['media']
            renditions = item.get('renditions', {})
            # push task capture preview thumbnail to video server
            project = {}
            if 'capture' in doc:
                # Remove empty value in updates to avoid cerberus return invalid input error
                capture = doc.pop('capture')
                if capture:
                    project = self.videoEditor.capture_preview_thumbnail(media_id, position=capture.get('position'),
                                                                         crop=capture.get('crop'),
                                                                         rotate=capture.get('rotate')
                                                                         )
                    renditions.setdefault('thumbnail', {}).update({
                        'href': project['thumbnails']['preview'].get('url'),
                        'mimetype': project['thumbnails']['preview'].get('mime_type', 'image/png'),
                    })
            # push task edit video to video server
            if 'edit' in doc:
                edit = doc.pop('edit')                
                if edit:
                    project = self.videoEditor.edit(media_id, edit)
                    renditions.setdefault('original', {}).update({
                        'href': project['url'],
                        'version': project['version'] + 1,
                        'video_editor_id': media_id,
                    })
            if renditions:
                updates = self.patch(item_id, {
                    'renditions': renditions,
                    'media': media_id,
                })
                item.update(updates)
            ids.append(item_id)
        return ids

    def find_one(self, req, **lookup):
        res = super().find_one(req, **lookup)
        if req is None:
            return res
        action = req.args.get('action')
        video_id = res['media']
        response = None
        if action == 'timeline':
            response = self.videoEditor.create_timeline_thumbnails(video_id, req.args.get('amount', 40))
            return {
                config.ID_FIELD: video_id,
                **response
            }
        res['project'] = self.videoEditor.find_one(video_id)
        return res

    def on_replace(self, document, original):
        """
        Override to upload thumbnails
        """
        if not document.get('file'):
            return
        # avoid dump file storage
        file = document.pop('file')
        project = original.pop('project')
        data = self.videoEditor.upload_preview_thumbnail(project.get('_id'), file)
        document.update(original)
        renditions = document.get('renditions', {})
        renditions.setdefault('thumbnail', {}).update({
            'href': data.get('url'),
            'mimetype': data.get('mimetype'),
        })
        document.update({'renditions': renditions})
        return document


class VideoEditResource(superdesk.Resource):
    item_methods = ['GET', 'PUT', 'PATCH']
    resource_methods = ['POST']
    privileges = {
        'POST': ARCHIVE,
        'PUT': ARCHIVE,
        'PATCH': ARCHIVE,
    }
    item_url = item_url
    schema = {
        'file': {'type': 'file'},
        'item': {'type': 'dict', 'required': False, 'empty': True},
        'edit': {'type': 'dict',
                 'required': False,
                 'empty': False,
                 'schema': {
                     'trim': {
                         'required': False,
                         'regex': '^\\d+\\.?\\d*,\\d+\\.?\\d*$',
                         'min_trim_start': 0,
                         'min_trim_end': 1

                     },
                     'rotate': {
                         'type': 'integer',
                         'required': False,
                         'allowed': [-270, -180, -90, 90, 180, 270]
                     },
                     'scale': {
                         'type': 'integer',
                         'required': False
                     },
                     'crop': {
                         'required': False,
                         'regex': '^\\d+,\\d+,\\d+,\\d+$'
                     }
                 }
                 },
        'capture': {'type': 'dict',
                    'required': False,
                    'empty': False,
                    'schema': {
                        'trim': {
                            'required': False,
                            'regex': '^\\d+\\.?\\d*,\\d+\\.?\\d*$',
                            'min_trim_start': 0,
                            'min_trim_end': 1

                        },
                        'rotate': {
                            'type': 'integer',
                            'required': False,
                            'allowed': [-270, -180, -90, 90, 180, 270]
                        },
                        'scale': {
                            'type': 'integer',
                            'required': False
                        },
                        'crop': {
                            'required': False,
                            'regex': '^\\d+,\\d+,\\d+,\\d+$'
                        }
                    }
                    },
    }

def init_app(app):
    video_edit_service = VideoEditService(ARCHIVE, backend=superdesk.get_backend())
    VideoEditResource('video_edit', app=app, service=video_edit_service)
