import superdesk
from superdesk import config
from superdesk.media.video_editor import VideoEditorService
from superdesk.errors import SuperdeskApiError


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
        if req is None:
            return super().find_one(req, **lookup)

        action = req.args.get('action')
        _id = lookup['_id']

        response = None
        if action == 'timeline':
            response = self.video_editor.get_timeline_thumbnails(_id, req.args.get('amount', 40))
        elif action == 'preview':
            response = self.video_editor.get_preview_thumbnail(
                project_id=_id,
                position=req.args.get('position'),
                crop=req.args.get('crop'),
                rotate=req.args.get('rotate')
            )

        if type(response) is dict and response.get('processing'):
            return {
                config.ID_FIELD: _id,
                **response
            }

        doc = self.video_editor.get(lookup['_id'])
        return doc


class VideoEditResource(superdesk.Resource):
    item_methods = ['GET']
    resource_methods = ['POST']
    privileges = {
        'POST': 'archive',
        'PUT': 'archive',
    }
    schema = {
        'file': {'type': 'file', 'required': False, 'empty': True},
        'item': {'type': 'dict', 'required': False, 'empty': True},
        'thumbnail': {'type': 'dict', 'required': False, 'empty': True},
        'edit': {'type': 'dict', 'required': False, 'empty': True},
    }


def init_app(app):
    video_edit_service = VideoEditService('archive', backend=superdesk.get_backend())
    VideoEditResource('video_edit', app=app, service=video_edit_service)
