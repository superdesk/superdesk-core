"""WSGI entrypoint.

Usage via Procfile:

    rest: gunicorn -c pythong:superdesk.gunicorn superdesk.wsgi

For debug mode, run it as: ``python -m superdesk.wsgi``.
"""

import os

from superdesk.factory import get_app

application = get_app()

if __name__ == '__main__':
    debug = True
    host = '0.0.0.0'
    port = int(os.environ.get('PORT', '5000'))
    application.run(host=host, port=port, debug=debug, use_reloader=debug)
