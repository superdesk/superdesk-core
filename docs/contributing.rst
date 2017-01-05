.. _contributing:

Contributing
============

Documentation
-------------
Superdesk documentation is written using `rst <http://docutils.sourceforge.net/rst.html>`_ format and generated via `Sphinx <http://www.sphinx-doc.org/>`_. It's organized by topic, using `autodoc <http://www.sphinx-doc.org/en/stable/ext/autodoc.html>`_ as much as possible to include docstrings from python code.

When working on docs, you can use live preview. In docs folder with virtualenv enabled run::

    $ make livehtml

This will build docs and run a server on ``localhost:8000``. It will refresh as you modify documentation, but not when you modify python docstrings, in order to see some changes done there you still have to make some changes in rst files.

Once you make a PR and it gets merged, you will see updated docs on `superdesk.readthedocs.io <http://superdesk.readthedocs.io/>`_.

Updating docs
^^^^^^^^^^^^^
Documentation should be added/updated together with code changes in a single PR to `superdesk-core <https://github.com/superdesk/superdesk-core>`_ repository. There can be also PRs with only documentation.

New topic/module
^^^^^^^^^^^^^^^^
To add a new topic or module docs, you create a file eg. ``foo.rst`` in ``docs`` folder and then you have to add it to ``index.rst`` `toctree <http://www.sphinx-doc.org/en/stable/markup/toctree.html>`_. This will make it appear in table of contents in both sidebar and on homepage.

Docs conventions
^^^^^^^^^^^^^^^^
Again - we should use `autodocs <http://www.sphinx-doc.org/en/stable/ext/autodoc.html>`_ as much as possible so that documentation is close to code and thus should get updated with it. Thus to document a class or function, use `autoclass <http://www.sphinx-doc.org/en/stable/ext/autodoc.html#directive-autoclass>`_ and `autofunction <http://www.sphinx-doc.org/en/stable/ext/autodoc.html#directive-autofunction>`_::

    .. autoclass:: apps.publish.content.common.BasePublishService
        :members:

    .. autofunction:: superdesk.publish.transmit

If you want to document multiple classes/functions from same module, you should use `automodule <http://www.sphinx-doc.org/en/stable/domains.html#directive-py:module>`_ or `module <http://www.sphinx-doc.org/en/stable/domains.html#directive-py:module>`_ first::

    .. module:: superdesk.io.feed_parsers

    .. autoclass:: ANPAFeedParser
    .. autoclass:: IPTC7901FeedParser

If you want to document whole module with all its members, you can just use `automodule <http://www.sphinx-doc.org/en/stable/ext/autodoc.html#directive-automodule>`_::

    .. automodule:: superdesk.io.feed_parsers
        :members:

This will document all public members from the module which have a docstring.

You can integrate UML diagrams using `PlantUML <http://plantuml.com/>`_ syntax, with::

    .. uml::

        [plantuml diagram]
