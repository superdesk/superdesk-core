"""Here you can import/implement macros.

This module will get reloaded per request to be up to date.

Use `superdesk.macro_register.macros.register` for registration.
"""

import os
import sys
import imp
import importlib
import logging


logger = logging.getLogger(__name__)


def load_macros(path, package_prefix='superdesk.macros'):
    """Load macros from given path

    :param str path:
    :param str package_prefix:
    """
    macros = [f[:-3] for f in os.listdir(path)
              if f.endswith('.py') and not f.endswith('_test.py') and not f.startswith('__')]

    for macro in macros:
        module = '{}.{}'.format(package_prefix, macro)
        try:
            if module in sys.modules.keys():
                m = sys.modules[module]
                imp.reload(m)
            else:
                importlib.import_module(module)
        except Exception as e:
            logger.warning("Can't import macro {module}: {reason}".format(module=module, reason=e))


macro_replacement_fields = {'body_html', 'body_text', 'abstract', 'headline', 'slugline', 'description_text'}
macros_folder = os.path.realpath(os.path.dirname(__file__))
load_macros(macros_folder)
