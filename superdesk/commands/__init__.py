from .clean_images import CleanImages  # noqa
from .rebuild_elastic_index import RebuildElasticIndex  # noqa
from .index_from_mongo import IndexFromMongo  # noqa
from .run_macro import RunMacro  # noqa
from .data_updates import *  # noqa
from .delete_archived_document import *  # noqa
from .update_archived_document import *  # noqa
from .remove_exported_files import RemoveExportedFiles  # noqa
from .flush_elastic_index import FlushElasticIndex  # noqa
from .generate_vocabularies import GenerateVocabularies  # noqa
from . import data_manipulation  # noqa
from . import schema  # noqa
from .async_cli import cli, commands_blueprint  # noqa
import superdesk


from superdesk.celery_app import celery


@celery.task()
def temp_file_expiry():
    RemoveExportedFiles()


def init_app(app) -> None:
    if app.config.get("SUPERDESK_TESTING", False):
        endpoint_name = "restore_record"
        service = data_manipulation.RestoreRecordService(endpoint_name, backend=superdesk.get_backend())
        data_manipulation.RestoreRecordResource(endpoint_name, app=app, service=service)

        superdesk.intrinsic_privilege(resource_name=endpoint_name, method=["POST"])


def configure_cli(app) -> None:
    """
    Sets the current app instance into the `AsyncAppGroup` to later be passed as context of the commands.
    It also registers the commands blueprint
    """
    cli.set_current_app(app)
    app.register_blueprint(commands_blueprint)
