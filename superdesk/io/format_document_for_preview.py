from superdesk.core import get_app_config
from superdesk.flask import Blueprint, request, Response
import superdesk
from superdesk import get_resource_service
from superdesk.publish.formatters import get_formatter
from superdesk.auth.decorator import blueprint_auth
from apps.content_types import apply_schema
from superdesk.types import SubscribersResource


bp = Blueprint("format_document", __name__)


def get_mime_type(formatter_qcode):
    if formatter_qcode == "newsmlg2":
        return "text/xml"
    else:
        return "application/json"


@bp.route("/format-document-for-preview/", methods=["GET", "OPTIONS"])
@blueprint_auth()
async def format_document():
    document_id = request.args.get("document_id")
    subscriber_id = request.args.get("subscriber_id")
    formatter_qcode = request.args.get("formatter")

    subscriber = await SubscribersResource.get_service().find_by_id_raw(subscriber_id)
    doc = await get_resource_service("archive").find_one_async(req=None, _id=document_id)

    formatter = get_formatter(formatter_qcode, doc)
    formatted_docs = await formatter.format(article=apply_schema(doc), subscriber=subscriber, codes=None)

    headers = {
        "Access-Control-Allow-Origin": get_app_config("CLIENT_URL"),
        "Access-Control-Allow-Methods": "GET",
        "Access-Control-Allow-Headers": ",".join(get_app_config("X_HEADERS")),
        "Access-Control-Allow-Credentials": "true",
        "Cache-Control": "no-cache, no-store, must-revalidate",
    }

    return Response(formatted_docs[0][1], headers=headers, mimetype=get_mime_type(formatter_qcode))


def init_app(app) -> None:
    superdesk.blueprint(bp, app)
