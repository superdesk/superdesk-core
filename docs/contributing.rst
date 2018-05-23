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

Formatter
---------

This is a short how-to to create a formatter.

Generic formatter are put in ``superdesk-core`` repository, you'll find them in ``superdesk/publish/formatters`` directory. Sometimes, we need to do custom version of formatter, in this case they are put in a fork of ``superdesk`` repository, in ``server/[fork_dir]/formatters``.

To create a new formatter, you can either subclass an existing one, or start fresh from ``superdesk.publish.formatters.Formatter``

.. autoclass:: superdesk.publish.formatters.Formatter
    :members:

The most important method here is ``format`` which is the one called with the article to format. This method must return a list of 2 elements tuples with a publish sequence number and the formatted output.
You can get publish sequence number using ``subscribers`` service:

.. code:: python

    pub_seq_num = superdesk.get_resource_service('subscribers').generate_sequence_number(subscriber)

You should wrap your ``format`` method in a ``try..except``, and raise a ``FormatterError`` if any problem arise.

.. autoclass:: superdesk.errors.FormatterError

Register formatter
^^^^^^^^^^^^^^^^^^

To use your formatter, you need to register it. This is done simply by importing your new module in ``superdesk.publish.formatters.__init__``. Here we do it for NITF:

.. code:: python

    from .nitf_formatter import NITFFormatter  # NOQA

Note the ``# NOQA`` which will avoid troubles with flake8 (the module is imported but not used immediately). The registration is done automatically thanks to the ``Formatter`` class.
