Feature: Places

    @auth
    Scenario: Places autocomplete 
        When we get "/places_autocomplete?name=koberice&lang=cs"
        # we use __any_value__ for states because we
        # can get either "XXX" or "XXX kraj" (e.g. "Olomoucký kraj" or "Olomoucký")
        Then we get list with 3 items
        """
        {
            "_items": [
                {
                    "code": "3073494",
                    "continent_code": "",
                    "country": "\u010cesko",
                    "country_code": "CZ",
                    "feature_class": "P",
                    "location": {
                        "lat": 49.3719,
                        "lon": 17.11262
                    },
                    "name": "Kobe\u0159ice",
                    "region": "",
                    "region_code": "",
                    "scheme": "geonames",
                    "state": "__any_value__",
                    "state_code": "84"
                },
                {
                    "code": "3073495",
                    "continent_code": "",
                    "country": "\u010cesko",
                    "country_code": "CZ",
                    "feature_class": "P",
                    "location": {
                        "lat": 49.08713,
                        "lon": 16.88324
                    },
                    "name": "Kobe\u0159ice",
                    "region": "",
                    "region_code": "",
                    "scheme": "geonames",
                    "state": "__any_value__",
                    "state_code": "78"
                },
                {
                    "code": "3073493",
                    "continent_code": "",
                    "country": "\u010cesko",
                    "country_code": "CZ",
                    "feature_class": "P",
                    "location": {
                        "lat": 49.98548,
                        "lon": 18.05212
                    },
                    "name": "Kobe\u0159ice",
                    "region": "",
                    "region_code": "",
                    "scheme": "geonames",
                    "state": "__any_value__",
                    "state_code": "85"
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
        When we get "/places_autocomplete?name=koberice&lang=cs"
        Then we get list with 6 items
        When we get "/places_autocomplete?name=koberice&lang=cs&featureClass=P"
        Then we get list with 3 items
