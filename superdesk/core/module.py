# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2024 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from typing import Callable, Optional
from dataclasses import dataclass


@dataclass
class Module:
    """Class used to register modules with the app"""

    #: The name of the module, used to identify the module
    #: as well as when overriding the module
    name: str

    #: Optional function to initialize the module
    init: Optional[Callable[["SuperdeskAsyncApp"], None]] = None

    #: if ``True``, does not allow overriding the module
    frozen: bool = False

    #: loading priority for the module, loads in descending order
    priority: int = 0

    #: path to the loaded module, populated by the app on load
    path: str = ""


from .app import SuperdeskAsyncApp  # noqa: E402
