# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013-2019 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import abc
import logging

logger = logging.getLogger(__name__)

registered_ai_services = {}


class AIServiceRegisterer(abc.ABCMeta):
    def __call__(cls, *args, **kwargs):
        instance = super().__call__(*args, **kwargs)
        name = instance.name
        if name in registered_ai_services:
            # we log a warning but don't raise an exception because the issue
            # may happen with tests
            logger.warning('"{name}" ai service is already registered'.format(name=name))
            return registered_ai_services[name]

        registered_ai_services[name] = instance
        return instance


class AIServiceBase(metaclass=AIServiceRegisterer):
    """Base class for AI service.

    This class define the attribute and methods mandatory to implement.
    AI services are automatically instanciated and registered, you just need to
    inherit from this class in your module.
    "label" attribute can be used, if it is not present the name will be used as label
    """

    def __init__(self, app):
        pass

    @property
    @abc.abstractmethod
    def name(self):
        pass

    @property
    def label(self):
        return self.name.title()

    @abc.abstractmethod
    def analyze(self, item: dict) -> dict:
        """Analyze article"""
        pass
