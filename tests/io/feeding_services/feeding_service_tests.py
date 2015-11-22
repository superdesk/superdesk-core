# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


from superdesk.tests import TestCase
from unittest import mock


class RegisterFeedingServiceTest(TestCase):
    """Base class for AutoRegisteredMeta metaclass tests."""

    def _get_target_metacls(self):
        """Return the metaclass under test.

        Make the test fail immediately if the metaclass cannot be imported.
        """
        try:
            from superdesk.io.feeding_services import RegisterFeedingService
        except ImportError:
            self.fail("Could not import metaclass under test (RegisterFeedingService).")
        else:
            return RegisterFeedingService


@mock.patch('superdesk.io.feeding_services.register_feeding_service')
class CreatingNewClassTestCase(RegisterFeedingServiceTest):
    """Tests for the new class creation process."""

    def test_creates_new_class_on_invocation(self, fake_register):
        metacls = self._get_target_metacls()

        BaseCls = type('BaseCls', (), {})
        new_class = metacls('NewClass', (BaseCls,), {'foo': 'bar', 'baz': 42})

        self.assertEqual(new_class.__name__, 'NewClass')
        self.assertTrue(issubclass(new_class, BaseCls))

        self.assertTrue(hasattr(new_class, 'foo'))
        self.assertEqual(new_class.foo, 'bar')
        self.assertTrue(hasattr(new_class, 'baz'))
        self.assertEqual(new_class.baz, 42)

    @mock.patch('superdesk.io.feeding_services.registered_feeding_services', {})
    def test_registers_new_feeding_service_classes(self, fake_register):
        metacls = self._get_target_metacls()

        new_class_errors = [(1234, 'Error 1234')]
        new_class = metacls('NewFeedingService', (), dict(ERRORS=new_class_errors, NAME='feeding_service_name'))

        self.assertTrue(fake_register.called)
        args, _ = fake_register.call_args
        self.assertEqual(len(args), 3)

        self.assertEqual(args[0], 'feeding_service_name')
        self.assertIs(args[1], new_class)
        self.assertEqual(args[2], new_class_errors)

    def test_does_not_register_non_feeding_service_classes(self, fake_register):
        metacls = self._get_target_metacls()
        metacls('NewClass', (), {})  # NOTE: no NAME attribute
        self.assertFalse(fake_register.called)

    @mock.patch('superdesk.io.feeding_services.registered_feeding_services', {'feeding_service_x': 'ClassX'})
    def test_raises_error_on_duplicate_feeding_service_name(self, fake_register):
        metacls = self._get_target_metacls()

        try:
            with self.assertRaises(TypeError) as exc_context:
                metacls('NewFeedingService', (), dict(ERRORS=[], NAME='feeding_service_x'))
        except:
            self.fail('Expected exception type was not raised.')

        ex = exc_context.exception
        self.assertEqual(str(ex), "Feeding Service feeding_service_x already exists (ClassX).")

    def test_raises_error_if_feeding_service_class_lacks_errors_attribute(self, fake_register):
        metacls = self._get_target_metacls()
        try:
            with self.assertRaises(AttributeError) as exc_context:
                metacls('NewFeedingService', (), {'NAME': 'foo'})  # NOTE: no ERRORS attribute
        except:
            self.fail("Expected exception type was not raised.")

        ex = exc_context.exception
        self.assertEqual(str(ex), "Feeding Service Class NewFeedingService must define the ERRORS list attribute.")


class FeedingServiceTest(TestCase):
    """Tests for the base FeedingService class."""

    def _get_target_class(self):
        """Return the class under test.

        Make the test fail immediately if the class cannot be imported.
        """
        try:
            from superdesk.io.feeding_services import FeedingService
        except ImportError:
            self.fail("Could not import class under test (FeedingService).")
        else:
            return FeedingService

    def test_has_correct_metaclass(self):
        from superdesk.io.feeding_services import RegisterFeedingService
        klass = self._get_target_class()
        self.assertIsInstance(klass, RegisterFeedingService)
