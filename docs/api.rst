API
===

Here is a quick overview of Superdesk API


Media Editor
------------
Media Editor do requested transformations on a media (images only for now).

client can use "media_editor" endpoint to transform an image.
A `POST` request needs to specify a whole `item` or an `item_id` and an `edit` object with edition
instructions.

Edition instructions keys are operations names, and values are
operations parameters.

So far, the following operations are available:

- rotate (value are counter clockwise degrees)
- flip (value can be "vertical", "horizontal" or "both")
- brightness (value is a float)
- contrast (value is a float)
- saturation (value is a float)
- grayscale (value not used)

In the answer, the API will return an `item` object with updated
renditions.

Request example:

.. code:: javascript

    {"item": {...}, "edit": {"brightness": 1.1, "contrast": 1.2, "rotate": -90}}
