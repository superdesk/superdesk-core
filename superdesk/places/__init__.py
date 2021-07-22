"""Superdesk places module.

Provides places autocomplete and search.
"""

import superdesk

from .places_autocomplete import PlacesAutocompleteResource, PlacesAutocompleteService


def init_app(app) -> None:
    if app.config.get("GEONAMES_USERNAME"):
        superdesk.register_resource(
            "places_autocomplete", PlacesAutocompleteResource, PlacesAutocompleteService, _app=app
        )
