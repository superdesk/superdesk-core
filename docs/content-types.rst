Content Profiles
================

Content profiles let you change the way how your content
should be edited and what validation rules should apply.

Definition
----------

You can specify custom profiles in ``server/data/content_types.json`` file.

Then you can sync it with database using cli command::

    python manage.py app:initialize_data --entity-name content_types

In the file there should be list of profiles::

    [
        {"_id": "story", "label": "Story", "enabled": 1, ...},
        {"_id": "snap", "label": "Snap", "enabled": 0, ...}
    ]

Available fields are:

``_id`` *string*
    Profile id, its value will be set in ``item.profile`` field and will be available in output.

``label`` *string*
    Label visible in the client.

``description`` *string*
    Optional profile description.

``priority`` *int*
    Used for sorting in descending order.

``enabled`` *boolean*
    Flag if profile is enabled (visible in lists) or not.

``schema`` *dict*
    Schema configuration for profile. There you can define validation rules for :ref:`schema` fields::

        "schema": {
            "headline": {
                "type": "string",
                "required": true,
                "maxlength": 120,
            },
            "keywords": {
                "type": "list",
                "required": true,
                "allowed": ["sport", "news"]
            }
        }

    Keys are field names, and for each field you can specify:

    ``type`` *string*
        One of ``string``, ``list``, ``dict``, ``integer``, ``number``.

    ``required`` *boolean*
        If ``true``, field must be there and be non empty.

    ``minlength``, ``maxlength`` *int*
        Minimum and maximum length allowed for ``string`` type.

    ``allowed`` *list*
        List of allowed values for ``string`` or ``list`` type.

    ``schema`` *dict*
        Validation rules for ``dict`` type items.

    ``nullable`` *boolean*
        If `True` the value can be set to ``null``.

    ``regex`` *string*
        Regex validation rule, eg.::

            "regex": "[a-z]+"

``editor`` *dict*
    Editor configuration for profile, there you can set what fields will
    be visible and how these should be displayed::

        "editor": {
            "headline": {
                "order": 1,
                "sdWidth": "full",
                "enabled": true
            },
            "body_html": {
                "order": 5,
                "formatOptions": ["h2", "bold", "italic"],
                "enabled": true
            },
            "ednote": {
                "enabled": false
            }
        }

    Rules for fields are:

    ``order`` *int*
        Where the field is visible in the editor.
    
    ``sdWidth`` *string*
        One of ``full``, ``half`` and ``quarter``. Fields are floating so there can be more on the same line
        as long as they fit there.

    ``enabled`` *boolean*
        If ``false`` field won't be visible in the editor.

    ``formatOptions`` *list*
        What format options should be available, only works with ``body_html`` and ``abstract`` fields.
        For each there will be a button visible in the editor toolbar.

        ``h2``

        ``bold``

        ``italic``

        ``underline``

        ``quote``

        ``anchor``

        ``embed``

        ``picture``

        ``removeFormat``


Available schema fields
-----------------------

These are fields you can use in your content profile:

.. autoclass:: superdesk.default_schema.DefaultSchema
    :members:

Plain text profile
------------------

Before there are any content profiles defined for a desk there is one called *Plain text*.


Package profiles
----------------

Package profiles are not yet supported.
