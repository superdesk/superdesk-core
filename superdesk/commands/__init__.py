from .clean_images import CleanImages  # noqa
from .rebuild_elastic_index import RebuildElasticIndex  # noqa
from .index_from_mongo import IndexFromMongo  # noqa
from .run_macro import RunMacro  # noqa
from .data_updates import *  # noqa
from .delete_archived_document import *  # noqa
from .update_archived_document import *  # noqa
from .remove_exported_files import RemoveExportedFiles  # noqa
from .flush_elastic_index import FlushElasticIndex # noqa
from .generate_vocabularies import GenerateVocabularies # noqa

from superdesk.celery_app import celery


@celery.task()
def temp_file_expiry():
    RemoveExportedFiles()
