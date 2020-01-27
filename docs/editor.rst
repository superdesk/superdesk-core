.. _editor:

Editor
======

If you want to modify fields managed by the editor (e.g. ``headline`` or  ``body_html``),
with a macro for instance, you need to use the EditorContent class which is an abstraction
used to manipulate the content. This is needed because since Editor 3, the HTML is managed
from internal representation of data. This page explains how to modify it.

.. note::

    with editor 2 you can directly modify ``body_html`` or ``headline`` fields


Modifying an HTML content from backend
--------------------------------------

You first need to create an instance of editor_content.
The following example show how to add an embedded code at the top of the body:

.. code:: python

   from superdesk.editor_utils import EditorContent

   def some_method_getting_an_item(item):
       body_editor = EditorContent.create(item, 'body_html')
       body_editor.prepend('embed', '<p class="some_class">some embedded HTML to
       prepend</p>')
       body_editor.update_item()
