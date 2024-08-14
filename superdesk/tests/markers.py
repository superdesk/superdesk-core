from pytest import mark

# Skips the test, due to known issue with async changes
# Change this to `requires_async_celery = mark.requires_async_celery` to run these tests
requires_async_celery = mark.skip(reason="Requires celery to support async tasks")

# Skips the test, due to test client not sending Authorization header in correct format
requires_auth_headers_fix = mark.skip(reason="Requires authorization headers fix")

# Skips the test, due to async events not currently supported with `on_` eve resource events
requires_eve_resource_async_event = mark.skip(reason="Requires eve resources to support async 'on_' events")

# Skips the test, requires investigation into the cause of the test failure
investigate_cause_of_error = mark.skip(reason="Test fails due to currently unknown reason")
