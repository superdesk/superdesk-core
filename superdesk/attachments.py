
import os
import superdesk

from flask import request
from werkzeug.utils import secure_filename
from apps.auth import get_user_id


class AttachmentsResource(superdesk.Resource):
    schema = {
        'media': {'type': 'media'},
        'mimetype': {'type': 'string'},
        'filename': {'type': 'string'},
        'size': {'type': 'integer'},
        'title': {'type': 'string'},
        'description': {'type': 'string'},
        'user': superdesk.Resource.rel('users'),
    }

    item_methods = ['GET', 'PATCH', 'DELETE']
    resource_methods = ['GET', 'POST']
    privileges = {'POST': 'attachments', 'PATCH': 'attachments', 'DELETE': 'attachments'}


class AttachmentsService(superdesk.Service):
    def on_create(self, docs):
        for doc in docs:
            doc['user'] = get_user_id()
            if request.files['media']:
                file = request.files['media']
                doc.setdefault('filename', secure_filename(os.path.basename(file.filename)))
                doc.setdefault('mimetype', file.mimetype)


def init_app(app):
    superdesk.register_resource('attachments', AttachmentsResource, AttachmentsService)
    superdesk.privilege(name='attachments', label='Attachments', description='User can add attachments.')
    app.client_config['attachments_max_files'] = app.config.get('ATTACHMENTS_MAX_FILES', 10)
    app.client_config['attachments_max_size'] = app.config.get('ATTACHMENTS_MAX_SIZE', 2 ** 20 * 8)  # 8MB
