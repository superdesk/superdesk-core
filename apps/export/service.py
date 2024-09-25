import logging
import re

from superdesk.core import get_current_app, json
from superdesk.services import BaseService
from superdesk import get_resource_service
from superdesk.errors import FormatterError, SuperdeskApiError
from superdesk.publish.formatters import get_all_formatters
from superdesk.utils import get_random_string
from superdesk.validation import ValidationError
from io import BytesIO
from zipfile import ZipFile
from quart_babel import gettext as _

logger = logging.getLogger(__name__)


class ExportService(BaseService):
    def create(self, docs, **kwargs):
        doc = docs[0]
        formatter = self._validate_and_get_formatter(doc)

        validate = doc.get("validate", False)
        archive_service = get_resource_service("archive")

        items = {}
        unsuccessful_exports = 0

        for item_id in doc.get("item_ids"):
            item = archive_service.find_one(req=None, _id=item_id)
            if item:
                if validate:
                    try:
                        self._validate_for_publish(item)
                    except ValidationError:
                        unsuccessful_exports += 1
                        continue

                try:
                    contents = formatter.export(item)
                except FormatterError as e:
                    logger.exception(e)
                    unsuccessful_exports += 1
                    continue

                # Remove invalid filename chars (for windows OS) and create the filename
                filename = (
                    re.sub(r'[\\/*?:"<>|]', "", item.get("slugline", "")) + "_" + str(item.get("unique_id")) + ".txt"
                )

                items[item_id] = filename, contents

        doc["failures"] = unsuccessful_exports

        if not items:
            return [len(docs)]

        if doc.get("inline"):
            doc["export"] = {}
            for item_id, (filename, contents) in items.items():
                try:
                    doc["export"][item_id] = json.loads(contents)
                except ValueError:
                    doc["export"][item_id] = contents
        else:
            in_memory_zip = BytesIO()
            with ZipFile(in_memory_zip, "a") as zip:
                for item_id, (filename, contents) in items.items():
                    zip.writestr(filename, contents.encode("UTF-8"))

            app = get_current_app()
            zip_id = app.media.put(
                in_memory_zip.getvalue(),
                filename="export_{}.zip".format(get_random_string()),
                content_type="application/zip",
                folder="temp",
            )
            doc["url"] = app.media.url_for_download(zip_id, "application/zip")

        return [len(docs)]

    def _validate_for_publish(self, doc):
        """Validates the given story for publish action"""
        validate_item = {"act": "publish", "type": doc["type"], "validate": doc}
        validation_errors = get_resource_service("validate").validate(validate_item)
        if validation_errors:
            raise ValidationError(validation_errors)

    def _validate_and_get_formatter(self, doc):
        """Validates incoming request and gets the formatter to be used"""
        if doc.get("item_ids") == 0:
            raise SuperdeskApiError.badRequestError(_("No items to export."))

        formatter_name = doc.get("format_type")
        formatter = next((f for f in get_all_formatters() if type(f).__name__ == formatter_name), None)
        if not formatter:
            raise SuperdeskApiError.badRequestError(_("Formatter not found for requested format type."))

        return formatter
