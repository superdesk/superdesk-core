Feature: Places

    @auth
    Scenario: Places autocomplete 
        When we get "/places_autocomplete?name=koberice&lang=cs"
        Then we get list with 3+ items
        """
        {
            "_items": [
                {
                    "name": "Kobeřice",
                    "code": "3073493",
                    "scheme": "geonames",
                    "state": "Moravskoslezský kraj",
                    "country": "Česko",
                    "state_code": "80",
                    "country_code": "CZ",
                    "feature_class": "P",
                    "location": {
                        "lat": 49.98548,
                        "lon": 18.05212
                    }
                }
            ]
        }
        """
