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
from collections import namedtuple
from typing import Tuple

logger = logging.getLogger(__name__)

Spellchecker = namedtuple("Spellchecker", ["name"])
registered_spellcheckers = {}


class SpellcheckerCapacities:
    all_capacities = {"spelling", "grammar"}

    def __init__(self, capacities):
        if isinstance(capacities, str):
            capacities = {capacities}
        capacities = set(capacities)
        if not capacities <= self.all_capacities:
            raise ValueError("invalid capacities: {invalid}".format(invalid=capacities - self.all_capacities))
        self.capacities = capacities

    def serialize(self):
        return sorted(self.capacities)


class SpellcheckerRegisterer(abc.ABCMeta):
    def __call__(cls, *args, **kwargs):
        instance = super().__call__(*args, **kwargs)
        name = instance.name
        if name in registered_spellcheckers:
            # we log a warning but don't raise an exception because the issue
            # may happen with tests
            logger.warning('"{name}" spellchecker is already registered'.format(name=name))
            return registered_spellcheckers[name]

        instance.capacities = SpellcheckerCapacities(instance.capacities)
        if not instance.available():
            logger.warning('"{name}" spellchecker is not available'.format(name=name))
            return None
        registered_spellcheckers[name] = instance
        return instance


class SpellcheckerBase(metaclass=SpellcheckerRegisterer):
    """Base class for spellchecker.

    This class define the attribute and methods mandatory to implement.
    Spellcheckers are automatically instanciated and registered, you just need to
    inherit from this class in your module.
    "label" attribute can be used, if it is not present the name will be used as label
    """

    CHECK_TIMEOUT = (3, 5)
    SUGGEST_TIMEOUT = (3, 10)

    #: what this spellchecker can do (spelling, grammar)
    capacities: Tuple[str, ...] = ("spelling",)

    #: version of the spellchecker, None if unknown
    version = None

    def __init__(self, app):
        self.config = app.config

    @property
    @abc.abstractmethod
    def name(self):
        pass

    @property
    def label(self):
        return self.name.title()

    @property
    @abc.abstractmethod
    def languages(self):
        """List of RFC-5646 tags for languages supported by this spellchecker

        Special value ['*'] means that any language can be supported.
        """
        pass

    @abc.abstractmethod
    def check(self, text, language=None):
        """Check spelling in given text"""
        pass

    def get_language(self, language):
        if language is None:
            language = self.languages[0]
        return language.split("-", 1)[0].lower()

    def suggest(self, text, language=None):
        """Get suggestions to correct given text"""
        logger.debug('"suggest" is not implemented')
        return {"suggestions": []}

    def available(self):
        """Return True if the spellchecker is available

        override this method is spellcheck availability depends of something (e.g. a
        server launched)
        """
        return True

    def list2suggestions(self, suggest_list):
        """Convert a list of str to expected list of objects for suggestions

        :param list suggest_list: if of suggests strings
        :return list: list of suggestions in the dict format expected by client
        """
        return [{"text": s} for s in suggest_list]

    def serialize(self):
        data = {
            "name": self.name,
            "label": self.label,
            "capacities": self.capacities.serialize(),
            "languages": self.languages,
        }
        if self.version is not None:
            data["version"] = self.version
        return data
