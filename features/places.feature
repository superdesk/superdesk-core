Feature: Places

    @auth
    Scenario: Places autocomplete 
        When we get "/places_autocomplete?name=brno&lang=cs"
        # we use __any_value__ for states because we
        # can get either "XXX" or "XXX kraj" (e.g. "Jihomoravský kraj" or "Jihomoravský")
        Then we get list with 1+ items
        """
        {
            "_items": [
                {
                    "code": "3078610",
                    "continent_code": "",
                    "country": "\u010cesko",
                    "country_code": "CZ",
                    "feature_class": "P",
                    "location": {
                        "lat": 49.19522,
                        "lon": 16.60796
                    },
                    "name": "Brno",
                    "region": "",
                    "region_code": "",
                    "scheme": "geonames",
                    "state_code": "78"
                }
            ]
        }
        """

    @auth
    Scenario: Places autocomplete feature filter setting
        Given config update
        """
        {
            "GEONAMES_FEATURE_CLASSES": ["P", "A"]
        }
        """
        When we get "/places_autocomplete?name=jihomoravsky&lang=cs"
        Then we get list with 1+ items
        """
        {
            "_items": [
                {
                    "code": "3339536",
                    "country_code": "CZ",
                    "feature_class": "A",
                    "name": "Jihomoravsk\u00fd",
                    "scheme": "geonames",
                    "state_code": "78"
                }
            ]
        }
        """
        When we get "/places_autocomplete?name=jihomoravsky&lang=cs&featureClass=P"
        Then we get list with 0 items
