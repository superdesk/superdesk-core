.. _editor:

Editor
======

If you want to modify fields managed by the editor (e.g. ``headline`` or
``body_html``), with a macro for instance, you need to use the EditorContent
class which is an abstraction used to manipulate the content. This is needed
because since Editor 3, the HTML is managed from internal representation of
data. This page explains how to modify it.

Replace text
------------

In order to replace ``'old'`` text with ``'new'``, you can use `text_replace` helper::

    import superdesk.editor_utils as editor_utils

    editor_utils.text_replace(item, 'body_html', 'old', 'new')
    editor_utils.text_replace(item, 'headline', 'old', 'new', is_html=False)

Blocks filter
-------------

If you need to remove some blocks from content (paragraphs, tables, etc.)
you can use :py:func:`filter_blocks` method::

    import superdesk.editor_utils as editor_utils

    def atomic_filter(block):
        return block.type != 'ATOMIC'

    editor_utils.filter_blocks(item, 'body_html', atomic_filter)

This would remove all atomic blocks from `body_html` field.

Other changes
-------------

If you need to make some unsupported change, you can modify the state directly.
You first need to create an instance of editor_content. The following example
show how to add an embedded code at the top of the body::

   from superdesk.editor_utils import EditorContent

   def some_method_getting_an_item(item):
       body_editor = EditorContent.create(item, 'body_html')
       body_editor.prepend('embed', '<p class="some_class">some embedded HTML to
       prepend</p>')
       body_editor.update_item()

Rendering customisation
=======================

Sometimes, you may want to modify the behavior of the renderer.

embeds
------

Embeds can be modified before being rendered. For that, the ``EMBED_PRE_PROCESS`` setting
can be used. It is an iterable linking to callable. Each callable will get the data dict
where the ``html`` key contains the raw HTML, so it can modify it.
