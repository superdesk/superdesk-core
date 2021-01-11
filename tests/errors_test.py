# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk import errors
from superdesk.errors import IngestApiError, IngestFileError, ParserError, ProviderError, IngestFtpError
from superdesk.tests import TestCase, setup_notification
from nose.tools import assert_raises
from superdesk.tests import setup
import logging
import unittest


class MockLoggingHandler(logging.Handler):
    """Mock logging handler to check for expected logs."""

    def __init__(self, *args, **kwargs):
        self.reset()
        logging.Handler.__init__(self, *args, **kwargs)

    def emit(self, record):
        self.messages[record.levelname.lower()].append(record.getMessage())

    def reset(self):
        self.messages = {
            "debug": [],
            "info": [],
            "warning": [],
            "error": [],
            "critical": [],
        }


class SuperdeskErrorTestCase(unittest.TestCase):
    """Tests for the `superdesk.errors.SuperdeskError` class."""

    def _get_target_class(self):
        """Return the class under test.

        Make the test fail immediately if the class cannot be imported.
        """
        try:
            from superdesk.errors import SuperdeskError
        except ImportError:
            self.fail("Could not import class under test (SuperdeskError).")
        else:
            return SuperdeskError

    def test_sets_error_description_to_none_by_default(self):
        klass = self._get_target_class()
        instance = klass(1234)
        self.assertIsNone(instance.desc)

    def test_stores_given_detailed_error_description(self):
        klass = self._get_target_class()
        instance = klass(1234, desc="Detailed error description.")
        self.assertEqual(instance.desc, "Detailed error description.")

    def test_string_representation_of_the_instance_no_description(self):
        klass = self._get_target_class()
        instance = klass(1234)
        instance.code = 101
        instance.message = "Foobar error"
        instance.desc = None

        self.assertEqual(str(instance), "SuperdeskError Error 101 - Foobar error")

    def test_string_representation_of_the_instance_description_given(self):
        klass = self._get_target_class()
        instance = klass(1234)
        instance.code = 101
        instance.message = "Foobar error"
        instance.desc = "This is a detailed description"

        self.assertEqual(
            str(instance), ("SuperdeskError Error 101 - Foobar error " "Details: This is a detailed description")
        )


class ErrorsTestCase(TestCase):

    mock_logger_handler = {}

    def setUp(self):
        setup(context=self)
        setup_notification(context=self)
        mock_logger = logging.getLogger("test")
        self.mock_logger_handler = MockLoggingHandler()
        mock_logger.addHandler(self.mock_logger_handler)
        errors.logger = mock_logger
        errors.notifiers = []
        self.provider = {"name": "TestProvider"}

    def test_raise_apiGeneralError(self):
        with assert_raises(IngestApiError) as error_context:
            try:
                ex = Exception("Testing general API error")
                raise ex
            except Exception:
                raise IngestApiError.apiGeneralError(ex, self.provider)

        exception = error_context.exception
        self.assertEqual(exception.code, 4000)
        self.assertEqual(exception.message, "Unknown API ingest error")
        self.assertEqual(exception.provider_name, "TestProvider")

        self.assertIsNotNone(exception.system_exception)
        self.assertEqual(exception.system_exception.args[0], "Testing general API error")

        self.assertEqual(len(self.mock_logger_handler.messages["error"]), 1)
        self.assertEqual(
            self.mock_logger_handler.messages["error"][0],
            "IngestApiError Error 4000 - Unknown API ingest error: "
            "Testing general API error on channel TestProvider",
        )

    def test_raise_apiRequestError(self):
        with assert_raises(IngestApiError) as error_context:
            try:
                ex = Exception("Testing apiRequestError")
                raise ex
            except Exception:
                raise IngestApiError.apiRequestError(ex, self.provider)
        exception = error_context.exception
        self.assertTrue(exception.code == 4003)
        self.assertTrue(exception.message == "API ingest has request error")
        self.assertIsNotNone(exception.system_exception)
        self.assertEqual(exception.system_exception.args[0], "Testing apiRequestError")
        self.assertEqual(len(self.mock_logger_handler.messages["error"]), 1)
        self.assertEqual(
            self.mock_logger_handler.messages["error"][0],
            "IngestApiError Error 4003 - API ingest has request error: "
            "Testing apiRequestError on channel TestProvider",
        )

    def test_raise_apiTimeoutError(self):
        with assert_raises(IngestApiError) as error_context:
            try:
                ex = Exception("Testing apiTimeoutError")
                raise ex
            except Exception:
                raise IngestApiError.apiTimeoutError(ex, self.provider)
        exception = error_context.exception
        self.assertTrue(exception.code == 4001)
        self.assertTrue(exception.message == "API ingest connection has timed out.")
        self.assertIsNotNone(exception.system_exception)
        self.assertEqual(exception.system_exception.args[0], "Testing apiTimeoutError")
        self.assertEqual(len(self.mock_logger_handler.messages["error"]), 1)
        self.assertEqual(
            self.mock_logger_handler.messages["error"][0],
            "IngestApiError Error 4001 - API ingest connection has timed out.: "
            "Testing apiTimeoutError on channel TestProvider",
        )

    def test_raise_apiRedirectError(self):
        with assert_raises(IngestApiError) as error_context:
            try:
                ex = Exception("Testing apiRedirectError")
                raise ex
            except Exception:
                raise IngestApiError.apiRedirectError(ex, self.provider)
        exception = error_context.exception
        self.assertTrue(exception.code == 4002)
        self.assertTrue(exception.message == "API ingest has too many redirects")
        self.assertIsNotNone(exception.system_exception)
        self.assertEqual(exception.system_exception.args[0], "Testing apiRedirectError")
        self.assertEqual(len(self.mock_logger_handler.messages["error"]), 1)
        self.assertEqual(
            self.mock_logger_handler.messages["error"][0],
            "IngestApiError Error 4002 - API ingest has too many redirects: "
            "Testing apiRedirectError on channel TestProvider",
        )

    def test_raise_apiUnicodeError(self):
        with assert_raises(IngestApiError) as error_context:
            try:
                ex = Exception("Testing apiUnicodeError")
                raise ex
            except Exception:
                raise IngestApiError.apiUnicodeError(ex, self.provider)
        exception = error_context.exception
        self.assertTrue(exception.code == 4004)
        self.assertTrue(exception.message == "API ingest Unicode Encode Error")
        self.assertIsNotNone(exception.system_exception)
        self.assertEqual(exception.system_exception.args[0], "Testing apiUnicodeError")
        self.assertEqual(len(self.mock_logger_handler.messages["error"]), 1)
        self.assertEqual(
            self.mock_logger_handler.messages["error"][0],
            "IngestApiError Error 4004 - API ingest Unicode Encode Error: "
            "Testing apiUnicodeError on channel TestProvider",
        )

    def test_raise_apiParseError(self):
        with assert_raises(IngestApiError) as error_context:
            try:
                ex = Exception("Testing apiParseError")
                raise ex
            except Exception:
                raise IngestApiError.apiParseError(ex, self.provider)
        exception = error_context.exception
        self.assertTrue(exception.code == 4005)
        self.assertTrue(exception.message == "API ingest xml parse error")
        self.assertIsNotNone(exception.system_exception)
        self.assertEqual(exception.system_exception.args[0], "Testing apiParseError")
        self.assertEqual(len(self.mock_logger_handler.messages["error"]), 1)
        self.assertEqual(
            self.mock_logger_handler.messages["error"][0],
            "IngestApiError Error 4005 - API ingest xml parse error: " "Testing apiParseError on channel TestProvider",
        )

    def test_raise_apiNotFoundError(self):
        with assert_raises(IngestApiError) as error_context:
            try:
                ex = Exception("Testing apiNotFoundError")
                raise ex
            except Exception:
                raise IngestApiError.apiNotFoundError(ex, self.provider)
        exception = error_context.exception
        self.assertTrue(exception.code == 4006)
        self.assertTrue(exception.message == "API service not found(404) error")
        self.assertIsNotNone(exception.system_exception)
        self.assertEqual(exception.system_exception.args[0], "Testing apiNotFoundError")
        self.assertEqual(len(self.mock_logger_handler.messages["error"]), 1)
        self.assertEqual(
            self.mock_logger_handler.messages["error"][0],
            "IngestApiError Error 4006 - API service not found(404) error: "
            "Testing apiNotFoundError on channel TestProvider",
        )

    def test_raise_apiAuthError(self):
        with assert_raises(IngestApiError) as error_context:
            try:
                ex = Exception("Testing API authorization error")
                raise ex
            except Exception:
                raise IngestApiError.apiAuthError(ex, self.provider)

        exception = error_context.exception
        self.assertEqual(exception.code, 4007)
        self.assertEqual(exception.message, "API authorization error")
        self.assertEqual(exception.provider_name, "TestProvider")

        self.assertIsNotNone(exception.system_exception)
        self.assertEqual(exception.system_exception.args[0], "Testing API authorization error")

        self.assertEqual(len(self.mock_logger_handler.messages["error"]), 1)
        self.assertEqual(
            self.mock_logger_handler.messages["error"][0],
            "IngestApiError Error 4007 - API authorization error: "
            "Testing API authorization error on channel TestProvider",
        )

    def test_raise_folderCreateError(self):
        with assert_raises(IngestFileError) as error_context:
            try:
                ex = Exception("Testing folderCreateError")
                raise ex
            except Exception:
                raise IngestFileError.folderCreateError(ex, self.provider)
        exception = error_context.exception
        self.assertTrue(exception.code == 3001)
        self.assertTrue(exception.message == "Destination folder could not be created")
        self.assertIsNotNone(exception.system_exception)
        self.assertEqual(exception.system_exception.args[0], "Testing folderCreateError")
        self.assertEqual(len(self.mock_logger_handler.messages["error"]), 1)
        self.assertEqual(
            self.mock_logger_handler.messages["error"][0],
            "IngestFileError Error 3001 - Destination folder could not be created: "
            "Testing folderCreateError on channel TestProvider",
        )

    def test_raise_fileMoveError(self):
        with assert_raises(IngestFileError) as error_context:
            try:
                ex = Exception("Testing fileMoveError")
                raise ex
            except Exception:
                raise IngestFileError.fileMoveError(ex, self.provider)
        exception = error_context.exception
        self.assertTrue(exception.code == 3002)
        self.assertTrue(exception.message == "Ingest file could not be copied")
        self.assertIsNotNone(exception.system_exception)
        self.assertEqual(exception.system_exception.args[0], "Testing fileMoveError")
        self.assertEqual(len(self.mock_logger_handler.messages["error"]), 1)
        self.assertEqual(
            self.mock_logger_handler.messages["error"][0],
            "IngestFileError Error 3002 - Ingest file could not be copied: "
            "Testing fileMoveError on channel TestProvider",
        )

    def test_raise_parseMessageError(self):
        with assert_raises(ParserError) as error_context:
            try:
                ex = Exception("Testing parseMessageError")
                raise ex
            except Exception:
                raise ParserError.parseMessageError(ex, self.provider)
        exception = error_context.exception
        self.assertTrue(exception.code == 1001)
        self.assertTrue(exception.message == "Message could not be parsed")
        self.assertIsNotNone(exception.system_exception)
        self.assertEqual(exception.system_exception.args[0], "Testing parseMessageError")
        self.assertEqual(len(self.mock_logger_handler.messages["error"]), 1)
        self.assertEqual(
            self.mock_logger_handler.messages["error"][0],
            "ParserError Error 1001 - Message could not be parsed: "
            "Testing parseMessageError on channel TestProvider",
        )

    def test_parse_message_error_save_data(self):
        data = "some data"
        with assert_raises(ParserError):
            try:
                raise Exception("Err message")
            except Exception as ex:
                raise ParserError.parseMessageError(ex, self.provider, data=data)
        self.assertEqual(len(self.mock_logger_handler.messages["error"]), 1)
        message = self.mock_logger_handler.messages["error"][0]
        self.assertIn("file=", message)
        filename = message.split("file=")[1]
        with open(filename, "r") as file:
            self.assertEqual(data, file.read())

    def test_raise_parseFileError(self):
        with assert_raises(ParserError) as error_context:
            try:
                raise Exception("Testing parseFileError")
            except Exception as ex:
                raise ParserError.parseFileError("afp", "test.txt", ex, self.provider)
        exception = error_context.exception
        self.assertTrue(exception.code == 1002)
        self.assertTrue(exception.message == "Ingest file could not be parsed")
        self.assertIsNotNone(exception.system_exception)
        self.assertEqual(exception.system_exception.args[0], "Testing parseFileError")
        self.assertEqual(len(self.mock_logger_handler.messages["error"]), 1)
        message = self.mock_logger_handler.messages["error"][0]
        self.assertIn("ParserError Error 1002 - Ingest file could not be parsed", message)
        self.assertIn("Testing parseFileError on channel TestProvider", message)
        self.assertIn("source=afp", message)
        self.assertIn("file=test.txt", message)

    def test_raise_newsmlOneParserError(self):
        with assert_raises(ParserError) as error_context:
            try:
                raise Exception("Testing newsmlOneParserError")
            except Exception as ex:
                raise ParserError.newsmlOneParserError(ex, self.provider)
        exception = error_context.exception
        self.assertTrue(exception.code == 1004)
        self.assertTrue(exception.message == "NewsML1 input could not be processed")
        self.assertIsNotNone(exception.system_exception)
        self.assertEqual(exception.system_exception.args[0], "Testing newsmlOneParserError")
        self.assertEqual(len(self.mock_logger_handler.messages["error"]), 1)
        self.assertEqual(
            self.mock_logger_handler.messages["error"][0],
            "ParserError Error 1004 - NewsML1 input could not be processed: "
            "Testing newsmlOneParserError on channel TestProvider",
        )

    def test_raise_newsmlTwoParserError(self):
        with assert_raises(ParserError) as error_context:
            try:
                ex = Exception("Testing newsmlTwoParserError")
                raise ex
            except Exception:
                raise ParserError.newsmlTwoParserError(ex, self.provider)
        exception = error_context.exception
        self.assertTrue(exception.code == 1005)
        self.assertTrue(exception.message == "NewsML2 input could not be processed")
        self.assertIsNotNone(exception.system_exception)
        self.assertEqual(exception.system_exception.args[0], "Testing newsmlTwoParserError")
        self.assertEqual(len(self.mock_logger_handler.messages["error"]), 1)
        self.assertEqual(
            self.mock_logger_handler.messages["error"][0],
            "ParserError Error 1005 - NewsML2 input could not be processed: "
            "Testing newsmlTwoParserError on channel TestProvider",
        )

    def test_raise_nitfParserError(self):
        with assert_raises(ParserError) as error_context:
            try:
                ex = Exception("Testing nitfParserError")
                raise ex
            except Exception:
                raise ParserError.nitfParserError(ex, self.provider)
        exception = error_context.exception
        self.assertTrue(exception.code == 1006)
        self.assertTrue(exception.message == "NITF input could not be processed")
        self.assertIsNotNone(exception.system_exception)
        self.assertEqual(exception.system_exception.args[0], "Testing nitfParserError")
        self.assertEqual(len(self.mock_logger_handler.messages["error"]), 1)
        self.assertEqual(
            self.mock_logger_handler.messages["error"][0],
            "ParserError Error 1006 - NITF input could not be processed: "
            "Testing nitfParserError on channel TestProvider",
        )

    def test_raise_providerAddError(self):
        with assert_raises(ProviderError) as error_context:
            try:
                ex = Exception("Testing providerAddError")
                raise ex
            except Exception:
                raise ProviderError.providerAddError(ex, self.provider)
        exception = error_context.exception
        self.assertTrue(exception.code == 2001)
        self.assertTrue(exception.message == "Provider could not be saved")
        self.assertIsNotNone(exception.system_exception)
        self.assertEqual(exception.system_exception.args[0], "Testing providerAddError")
        self.assertEqual(len(self.mock_logger_handler.messages["error"]), 1)
        self.assertEqual(
            self.mock_logger_handler.messages["error"][0],
            "ProviderError Error 2001 - Provider could not be saved: "
            "Testing providerAddError on channel TestProvider",
        )

    def test_raise_expiredContentError(self):
        with assert_raises(ProviderError) as error_context:
            try:
                ex = Exception("Testing expiredContentError")
                raise ex
            except Exception:
                raise ProviderError.expiredContentError(ex, self.provider)
        exception = error_context.exception
        self.assertTrue(exception.code == 2002)
        self.assertTrue(exception.message == "Expired content could not be removed")
        self.assertIsNotNone(exception.system_exception)
        self.assertEqual(exception.system_exception.args[0], "Testing expiredContentError")
        self.assertEqual(len(self.mock_logger_handler.messages["error"]), 1)
        self.assertEqual(
            self.mock_logger_handler.messages["error"][0],
            "ProviderError Error 2002 - Expired content could not be removed: "
            "Testing expiredContentError on channel TestProvider",
        )

    def test_raise_ruleError(self):
        with assert_raises(ProviderError) as error_context:
            try:
                ex = Exception("Testing ruleError")
                raise ex
            except Exception:
                raise ProviderError.ruleError(ex, self.provider)
        exception = error_context.exception
        self.assertTrue(exception.code == 2003)
        self.assertTrue(exception.message == "Rule could not be applied")
        self.assertIsNotNone(exception.system_exception)
        self.assertEqual(exception.system_exception.args[0], "Testing ruleError")
        self.assertEqual(len(self.mock_logger_handler.messages["error"]), 1)
        self.assertEqual(
            self.mock_logger_handler.messages["error"][0],
            "ProviderError Error 2003 - Rule could not be applied: " "Testing ruleError on channel TestProvider",
        )

    def test_raise_ingestError(self):
        with assert_raises(ProviderError) as error_context:
            try:
                ex = Exception("Testing ingestError")
                raise ex
            except Exception:
                raise ProviderError.ingestError(ex, self.provider)
        exception = error_context.exception
        self.assertTrue(exception.code == 2004)
        self.assertTrue(exception.message == "Ingest error")
        self.assertTrue(exception.provider_name == "TestProvider")
        self.assertIsNotNone(exception.system_exception)
        self.assertEqual(exception.system_exception.args[0], "Testing ingestError")
        self.assertEqual(len(self.mock_logger_handler.messages["error"]), 1)
        self.assertEqual(
            self.mock_logger_handler.messages["error"][0],
            "ProviderError Error 2004 - Ingest error: " "Testing ingestError on channel TestProvider",
        )

    def test_raise_anpaError(self):
        with assert_raises(ProviderError) as error_context:
            try:
                ex = Exception("Testing anpaError")
                raise ex
            except Exception:
                raise ProviderError.anpaError(ex, self.provider)
        exception = error_context.exception
        self.assertTrue(exception.code == 2005)
        self.assertTrue(exception.message == "Anpa category error")
        self.assertIsNotNone(exception.system_exception)
        self.assertEqual(exception.system_exception.args[0], "Testing anpaError")
        self.assertEqual(len(self.mock_logger_handler.messages["error"]), 1)
        self.assertEqual(
            self.mock_logger_handler.messages["error"][0],
            "ProviderError Error 2005 - Anpa category error: " "Testing anpaError on channel TestProvider",
        )

    def test_raise_providerFilterExpiredContentError(self):
        with assert_raises(ProviderError) as error_context:
            try:
                ex = Exception("Testing providerFilterExpiredContentError")
                raise ex
            except Exception:
                raise ProviderError.providerFilterExpiredContentError(ex, self.provider)
        exception = error_context.exception
        self.assertTrue(exception.code == 2006)
        self.assertTrue(exception.message == "Expired content could not be filtered")
        self.assertIsNotNone(exception.system_exception)
        self.assertEqual(exception.system_exception.args[0], "Testing providerFilterExpiredContentError")
        self.assertEqual(len(self.mock_logger_handler.messages["error"]), 1)
        self.assertEqual(
            self.mock_logger_handler.messages["error"][0],
            "ProviderError Error 2006 - Expired content could not be filtered: "
            "Testing providerFilterExpiredContentError on channel TestProvider",
        )

    def test_raise_ftpError(self):
        with assert_raises(IngestFtpError) as error_context:
            try:
                ex = Exception("Testing ftpError")
                raise ex
            except Exception:
                raise IngestFtpError.ftpError(ex, self.provider)
        exception = error_context.exception
        self.assertTrue(exception.code == 5000)
        self.assertTrue(exception.message == "FTP ingest error")
        self.assertIsNotNone(exception.system_exception)
        self.assertEqual(exception.system_exception.args[0], "Testing ftpError")
        self.assertEqual(len(self.mock_logger_handler.messages["error"]), 1)
        self.assertEqual(
            self.mock_logger_handler.messages["error"][0],
            "IngestFtpError Error 5000 - FTP ingest error: " "Testing ftpError on channel TestProvider",
        )

    def test_raise_ftpUnknownParserError(self):
        with assert_raises(IngestFtpError) as error_context:
            try:
                raise Exception("Testing ftpUnknownParserError")
            except Exception as ex:
                raise IngestFtpError.ftpUnknownParserError(ex, self.provider, "test.xml")
        exception = error_context.exception
        self.assertTrue(exception.code == 5001)
        self.assertTrue(exception.message == "FTP parser could not be found")
        self.assertIsNotNone(exception.system_exception)
        self.assertEqual(exception.system_exception.args[0], "Testing ftpUnknownParserError")
        self.assertEqual(len(self.mock_logger_handler.messages["error"]), 1)
        self.assertEqual(
            self.mock_logger_handler.messages["error"][0],
            "IngestFtpError Error 5001 - FTP parser could not be found: "
            "Testing ftpUnknownParserError on channel TestProvider file=test.xml",
        )
