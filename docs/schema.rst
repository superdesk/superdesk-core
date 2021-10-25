.. _schema:

Item Schema
===========

.. automodule:: superdesk.metadata.item

Superdesk uses internally item schema that is an extension of ninjs,
so on ingest everything is converted to this schema, and on publishing
it's converted to different formats.

Basic Schema as defined in :data:`metadata_schema` dict:

Identifiers
-----------

``guid`` *string*

    Globally unique id. Using external id for ingested content.

``unique_id`` *integer*

    Internally unique id.

``unique_name`` *string*
    
    Internally unique name. By default same as ``unique_id``.

``family_id`` *string*

    Id for all items derived from single item via fetch or copy actions.
    For ingested items equals to ``ingest_id``.

``related_to`` *string*

    Original item id when doing associate metadata action.

Content metadata
----------------

``headline`` *string*

    Item headline.

``slugline`` *string*

    Item slugline.

``byline`` *string*

    Item byline.

``abstract`` *string*

    Perex or lead.

``keywords`` *list*

    List of keywords.

``word_count`` *integer*

    Word count in ``body_html`` field.

``priority`` *integer*

    Item priority.

``urgency`` *integer*

    Item urgency.

``description_text`` *string*

    Text description of the item. Used for media types.

``body_html`` *string*

    Main content field for text items.

``body_text`` *string*

    Text content of the item. Used for preformatted text.

``body_footer`` *string*

    Content footer, used for additional information.

``dateline`` *dict*

    Info about when/where story was written.

``groups`` *dict*

    Package contents in *NewsML* like format.

``media`` *string*

    Binary file reference for media type items.

``mimetype`` *string*

    Binary file mime type.

``poi`` *dict*

    Point of Interest on a picture.

    :param x: horizontal offset
    :param y: vertical offset

``renditions`` *dict*

    Renditions of a media type item::

        'renditions': {
            'original': {
                'href': '...',
                'width': 1280,
                'height': 800,
            },
            ...
        }

``filemeta`` *dict*

    Extracted file metadata. Mimetype specific.

    .. deprecated:: 1.2

``filemeta_json`` *string*

    JSON encoded filemeta. Avoids storage issues.

    .. versionadded:: 1.2

``associations`` *dict*

    Embedded items within body text or predefined relations::

        'associations': {
            'featured_image': {
                'type': 'picture',
                'guid': 'urn:localhost:123',
                ...
            }
        }

``alt_text`` *string*

    Alternate text for picture type items.

``sms_message`` *string*

    Short summary of an item, can be used for sms/twitter subscribers.

Item metadata
-------------

``type`` *string*

    Item type. One of ``text|composite|picture|audio|video``.


``language`` *string*

    Item language code.

``anpa_take_key`` *string*

    Take id.

``profile`` *string*

    Content profile id.

``state`` *string*

    Workflow state.

    .. autodata:: ContentStates

``revert_state`` *string*

    Previous item state, is updated on every state change.

``pubstatus`` *string*

    Publication state.

    .. autodata:: PubStatuses

``signal`` *string*

    Signal information sent to subscriber.

``ednote`` *string*

    Editorial comment.

``flags`` *dict*

    Various flags.

``expiry`` *datetime*

    When this item will expire.
    It updates on every save/send action.

Copyright information
^^^^^^^^^^^^^^^^^^^^^

``usageterms`` *string*

``copyrightnotice`` *string*

``copyrightholder`` *string*

``creditline`` *string*

CVs
---
These attributes are populated using values from controlled vocabularies.

``anpa_category`` *list*

    Values from category cv.

``subject`` *list*

    Values from `IPTC subjectcodes <https://iptc.org/standards/newscodes/>`_ plus from custom cvs.

``genre`` *list*

    Values from genre cv.

``company_codes`` *list*

    Values from company codes cv.

``place`` *list*

    Place where story happened.

System
------

Set/updated by system mostly.

``_current_version`` *integer*

    Version of an item, gets incremented on save or publish.

``version`` *integer*

    Set by client - used to create items with version ``0`` which are used as drafts.

``firstcreated`` *datetime*

    When the item was created.

``versioncreated`` *datetime*

    When current version was created.

``original_creator`` *id*

    User who created/fetched item.

``version_creator`` *id*

    User who created current version.

``lock_user`` *id*

    User who has lock.

``lock_time`` *datetime*

    When item was locked.

``lock_session`` *id*

    Session id where item was locked. This way it can detect items locked by same
    user but in different sessions.

``template`` *id*

    Template id if item was created using a template.

``published_in_package`` *id*

    If item was published as part of a package for the first time this will be set to package id.

Ingest
------
Set on ingest, might be empty for items created in house.

``ingest_id`` *string*

    Ingest item id from which item was fetched. For ingested items same as ``family_id``.

``ingest_provider`` *id*

    Ingest provider id.

``source`` *string*

    Ingest provider source value. Using ``DEFAULT_SOURCE_VALUE_FOR_MANUAL_ARTICLES`` config for
    items created locally.

``original_source`` *string*

    Source value from ingested item.

``ingest_provider_sequence`` *integer*

    Counter for ingest items.
