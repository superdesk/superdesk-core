import superdesk
from superdesk.upload import get_upload_as_data_uri
from flask import current_app as app


bp = superdesk.Blueprint('assets', __name__)


@bp.route('/assets/<path:media_id>', methods=['GET'])
def prod_get_upload_as_data_uri(media_id):
    return get_upload_as_data_uri(media_id)


def upload_url(media_id, view=prod_get_upload_as_data_uri):
    return '{}/{}'.format(
        app.config.get('MEDIA_PREFIX').rstrip('/'),
        media_id
    )


def init_app(app):
    superdesk.blueprint(bp, app)
    app.upload_url = upload_url
