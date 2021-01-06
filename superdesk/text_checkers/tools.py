# This file is part of Superdesk.
#
# Copyright 2019-2020 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import logging
from inspect import isclass
from pathlib import Path
from importlib import import_module

logger = logging.getLogger(__name__)


def import_services(
    app,
    pkg_name: str,
    base_cls: type,
) -> None:
    """Import all services based on base_cls in given package

    This method will import python modules and look for a base_cls subclass there
    If found, the subclass will be instantiated
    :param app: app instance
    :param str pkg_name: name of the package to use
    :param base_cls: base class of the service
    """
    pkg = import_module(pkg_name)
    for file_path in Path(pkg.__file__).parent.glob("*.py"):
        module_name = file_path.stem
        if module_name in ("__init__", "base"):
            continue
        service_mod = import_module(pkg_name + "." + module_name)
        for obj_name in dir(service_mod):
            if obj_name.startswith("__") or obj_name == base_cls.__name__:
                continue
            obj = getattr(service_mod, obj_name)
            if not isclass(obj):
                continue
            if issubclass(obj, base_cls):
                obj(app)
                break
        else:
            logger.warning("Can't find service in module {module_name}".format(module_name=module_name))
