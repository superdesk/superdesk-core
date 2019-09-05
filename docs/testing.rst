.. _testing:

Testing
=======

There are 2 main kinds of tests in superdesk: unit tests (run with ``nosetests``) and
behaviour-driven tests (run with ``behave``). You can use ``pip install -r
dev-requirements.txt`` in your Python environement to install the needed dependencies.



Mocking tests with behave
-------------------------

Behave tests are end-to-end, and may be using network calls. In some cases, we may desire
to keep the network access to detect an API change in external service (for instance it's
the case with `GeoNames`_), in other cases it's better to mock the call to avoid network
access to retrieve data on each run of tests (network access can slow down the whole
process, they may fail resulting in the whole test run failing, and they consume
resources).

If you want to mock network call in behave, you may, in some tests, append the text
``(mocking with "{mock_file}")`` where ``{mock_file}`` is the name of a ``JSON`` file
available in your fixtures directory. This files specify which URL to mock, and how to do
it.

Here is an example of a step using mocking::

  When we fetch from "ninjs" ingest "ninjs4.json" (mocking with "ninjs4_mock.json")


Here is an example of a typical mocking file:

.. code:: json


    {
        "requests": {
            "http://thumbs.dreamstime.com/z/digital-nature-10485007.jpg": {
                "get": {
                    "binary": "digital-nature-10485007.jpg"
                }
            }
        }
    }

It is a JSON object where key can, so far, only be ``requests``, meaning that you want
to mock an HTTP request (it works only for requests done using the `Python Requests`_
module).

The ``requests`` value is another object where each key is an URL to mock. The URL links
to an object containing the verb to mock (only ``GET`` is supported for now, the key is
case insensitive). Finally the verb link to and object containing the mocking data. You
may use one of the following key in this last object:

=======  ================================================================================
  key                                        use
=======  ================================================================================
binary   A file must be returned. The value is the name of the file to send, which must
         be in the same fixtures directory as the mocking file. ``content_type`` default
         to ``application/octet-stream``

text     A text is returned as body. ``content_type`` default to ``text/plain``

json     A ``JSON`` object is returned. ``content_type`` default to ``application/json``
=======  ================================================================================

If you don't want to use the default ``content_type``, you can specify another one in the
key of the same name.

.. _GeoNames: http://www.geonames.org/
.. _Python Requests: https://2.python-requests.org/
