
import unittest

from .spellcheck import norvig_suggest


class SpellcheckTestCase(unittest.TestCase):

    def test_suggestsions(self):

        model = {'foe': 3, 'fox': 5}
        suggestions = norvig_suggest('foo', model)
        self.assertEquals(['fox', 'foe'], suggestions)

    def test_suggestsions_case_insensitive(self):
        """Test case for getting the suggestions irrespective of the case(lower/upper) of the word"""

        model = {'Foe': 1, 'fox': 5}
        suggestions_lower = norvig_suggest('fooe', model)
        self.assertEquals(['foe'], suggestions_lower)

        suggestions_upper = norvig_suggest('Fooe', model)
        self.assertEquals(['foe'], suggestions_upper)
