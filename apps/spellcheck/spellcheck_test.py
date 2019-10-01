
import unittest

from .spellcheck import norvig_suggest


class SpellcheckTestCase(unittest.TestCase):

    def test_normal_suggestions(self):
        """Test case for getting the suggestions for the word which aren't name"""
        model = {'foe': 3, 'fox': 5}
        suggestions_1 = norvig_suggest('foo', model)
        self.assertEquals(['fox', 'Fox', 'foe', 'Foe'], suggestions_1)

        suggestions_2 = norvig_suggest('Foo', model)
        self.assertEquals(['fox', 'Fox', 'foe', 'Foe'], suggestions_2)

    def test_name_suggestions(self):
        """Test case for getting the suggestions for name in capitalized case"""

        model = {'Foe': 1, 'fox': 5}
        name_suggestion_1 = norvig_suggest('fooe', model)
        self.assertEquals(['Foe'], name_suggestion_1)

        name_suggestion_2 = norvig_suggest('Fooe', model)
        self.assertEquals(['Foe'], name_suggestion_2)
