import superdesk
from apps.archive.common import ARCHIVE
from superdesk import config
from superdesk.errors import SuperdeskApiError
from superdesk.media.video_editor import VideoEditorService
from superdesk.metadata.utils import item_url


class VideoEditService(superdesk.Service):
    """Edit video
    Use ffmpeg to create thumbnail and cutting video
    data req:
    """
    video_editor = VideoEditorService()

    def create(self, docs, **kwargs):
        ids = []
        for doc in docs:
            item = doc.get('item')
            item_id = item.get(config.ID_FIELD)
            media_id = item['media']
            renditions = item.get('renditions', {})
            # push task capture preview thumbnail to video server
            capture = {}
            edit = {}
            if 'capture' in doc:
                # Remove empty value in updates to avoid cerberus return invalid input error
                capture = validate_edit_data(doc.pop('capture'))
                if capture:
                    self.video_editor.get_preview_thumbnail(media_id, position=capture.get('position'),
                                                            crop=capture.get('crop'),
                                                            rotate=capture.get('rotate')
                                                            )
            # push task edit video to video server
            if 'edit' in doc:
                # Remove empty value in updates to avoid cerberus return invalid input error
                edit = validate_edit_data(doc.pop('edit'))
                # duplicate original video before edit to avoid override
                if edit:
                    if renditions.get('original', {}).get('version', 1) == 1:
                        response = self.video_editor.duplicate(media_id)
                        media_id = response.get('_id', media_id)
                    try:
                        self.video_editor.put(media_id, edit)
                    except SuperdeskApiError as ex:
                        if response:
                            self.video_editor.delete(media_id)
                        raise ex
            # get data video
            data = self.video_editor.get(media_id)
            if capture:
                renditions.setdefault('thumbnail', {}).update({
                    'href': data['thumbnails']['preview'].get('url'),
                    'mimetype': data['thumbnails']['preview'].get('mime_type'),
                })
            if edit:
                renditions.setdefault('original', {}).update({
                    'href': data['url'],
                    'media': data['_id'],
                    'mimetype': data['mime_type'],
                    'version': data['version'],
                })
            if renditions:
                updates = self.patch(item_id, {
                    'renditions': renditions,
                    'media': renditions['original']['media'],
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
            response = self.video_editor.get_timeline_thumbnails(video_id, req.args.get('amount', 40))
        elif action == 'preview':
            metadata = self.video_editor.get(video_id).get('metadata')
            position = req.args.get('position')
            if position > metadata.get('duration'):
                position = metadata.get('duration')
            response = self.video_editor.get_preview_thumbnail(
                project_id=video_id,
                position=position,
                crop=req.args.get('crop'),
                rotate=req.args.get('rotate')
            )

        if type(response) is dict and response.get('processing'):
            return {
                config.ID_FIELD: video_id,
                **response
            }
        res['project'] = self.video_editor.get(video_id)
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
        data = self.video_editor.post_preview_thumbnail(project.get('_id'), file)
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
        'edit': {'type': 'dict', 'required': False, 'empty': False},
        'capture': {'type': 'dict', 'required': False, 'empty': False},
    }


def validate_edit_data(data):
    for action in data.copy().keys():
        if not data[action]:
            data.pop(action)
            continue
        if action == 'crop':
            for k, v in data[action].items():
                if v < 0:
                    data[action][k] = 0
    return data


def init_app(app):
    video_edit_service = VideoEditService(ARCHIVE, backend=superdesk.get_backend())
    VideoEditResource('video_edit', app=app, service=video_edit_service)
