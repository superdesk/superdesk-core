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

            edit = doc.pop('edit')
            if edit:
                # Remove empty value in updates to avoid cerberus return invalid input error
                for action in edit.copy().keys():
                    if not edit[action]:
                        edit.pop(action)

                # duplicate original video before edit to avoid override
                if renditions.get('original', {}).get('version', 1) == 1:
                    response = self.video_editor.duplicate(media_id)
                    media_id = response.get('_id', media_id)

                try:
                    self.video_editor.put(media_id, edit)
                except SuperdeskApiError as ex:
                    if response.get('parent'):
                        self.video_editor.delete(media_id)
                    raise ex

                data = self.video_editor.get(media_id)
                renditions.setdefault('original').update({
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
                ids.append(updates)

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
            response = self.video_editor.get_preview_thumbnail(
                project_id=video_id,
                position=req.args.get('position'),
                crop=req.args.get('crop'),
                rotate=req.args.get('rotate')
            )

        if type(response) is dict and response.get('processing'):
            return {
                config.ID_FIELD: video_id,
                **response
            }

        return self.video_editor.get(video_id)

    def on_replace(self, document, original):
        """
        Override to upload thumbnails
        """
        if not document.get('file'):
            return

        file = document.pop('file')  # avoid dump file storage
        self.video_editor.post_preview_thumbnail(document['_id'], file)
        document.update(self.video_editor.get(document['_id']))


class VideoEditResource(superdesk.Resource):
    item_methods = ['GET', 'PUT']
    resource_methods = ['POST']
    privileges = {
        'POST': ARCHIVE,
        'PUT': ARCHIVE,
    }
    item_url = item_url
    schema = {
        'file': {'type': 'file'},
        'item': {'type': 'dict', 'required': False, 'empty': True},
        'edit': {'type': 'dict', 'required': False, 'empty': True},
    }


def init_app(app):
    video_edit_service = VideoEditService(ARCHIVE, backend=superdesk.get_backend())
    VideoEditResource('video_edit', app=app, service=video_edit_service)
