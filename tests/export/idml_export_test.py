import base64
import io
import zipfile
from unittest.mock import AsyncMock, MagicMock, patch

from apps.export.service import ExportService
from superdesk.publish.formatters.idml_formatter import IDMLFormatter
from superdesk.tests import TestCase

ARTICLE = {
    "_id": "x1",
    "guid": "x1",
    "type": "text",
    "headline": "Posto de saúde abre aos sábados",
    "slugline": "posto-saude",
    "unique_id": 7,
    "byline": "Ana Ribeiro",
    "body_html": "<p>O posto passa a abrir aos sábados.</p>",
}


def stories_text(idml: bytes) -> str:
    package = zipfile.ZipFile(io.BytesIO(idml))
    assert package.read("mimetype") == b"application/vnd.adobe.indesign-idml-package"
    return "".join(package.read(n).decode() for n in package.namelist() if n.startswith("Stories/"))


class IDMLExportTest(TestCase):
    def test_formatter_exports_idml_bytes(self):
        formatter = IDMLFormatter()
        self.assertTrue(formatter.can_export)
        self.assertIn("Posto de sa&#250;de", stories_text(formatter.export(dict(ARTICLE))))

    async def _export(self, doc):
        archive = MagicMock()
        archive.find_one_async = AsyncMock(return_value=dict(ARTICLE))
        with patch("apps.export.service.get_resource_service", return_value=archive):
            await ExportService().create_async([doc])
        return doc

    async def test_inline_export_is_base64(self):
        doc = await self._export({"item_ids": ["x1"], "format_type": "IDMLFormatter", "inline": True})
        self.assertIn("Ana Ribeiro", stories_text(base64.b64decode(doc["export"]["x1"])))

    async def test_zip_export_holds_an_idml_file(self):
        put_async = AsyncMock(return_value="zip1")
        with patch.object(self.app.media, "put_async", put_async), patch.object(
            self.app.media, "url_for_download", return_value="http://example/raw"
        ), patch("apps.export.service.generate_url_with_token", return_value="http://example/zip1"):
            doc = await self._export({"item_ids": ["x1"], "format_type": "IDMLFormatter"})
        self.assertEqual(doc["url"], "http://example/zip1")
        outer = zipfile.ZipFile(io.BytesIO(put_async.await_args.args[0]))
        self.assertEqual(outer.namelist(), ["posto-saude_7.idml"])
        self.assertIn("Ana Ribeiro", stories_text(outer.read("posto-saude_7.idml")))
