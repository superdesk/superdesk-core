
import superdesk


def norvig_suggest(word, model):
    """Norvig's simple spell check.

    Modified not to return only best correction, but all of them sorted.
    """
    NWORDS = model
    alphabet = 'abcdefghijklmnopqrstuvwxyz'
    suggestions = []

    def edits1(word):
        splits = [(word[:i], word[i:]) for i in range(len(word) + 1)]
        deletes = [a + b[1:] for a, b in splits if b]
        transposes = [a + b[1] + b[0] + b[2:] for a, b in splits if len(b) > 1]
        replaces = [a + c + b[1:] for a, b in splits for c in alphabet if b]
        inserts = [a + c + b for a, b in splits for c in alphabet]

        return set(deletes + transposes + replaces + inserts)

    def known_edits2(word):
        return set(e2 for e1 in edits1(word) for e2 in edits1(e1) if e2 in NWORDS)

    def known(words):
        return set(w for w in words if w in NWORDS)

    def suggest(word):
        candidates = known([word]) or known(edits1(word)) # or known_edits2(word)
        return sorted(candidates, key=lambda item: NWORDS.get(item, 1), reverse=True)

    name_suggestions = suggest(word.capitalize())
    # check if word suggestion is a name as we store name as capitalized case in dictionary
    if len(name_suggestions) == 1:
        return name_suggestions

    # if not name suggestion find all the suggestions by converting the word to lowercase
    # and make sure to send lowercase as well as capitalized case suggestions for normal words
    for suggestion in suggest(word.lower()):
        suggestions.extend([suggestion, suggestion.capitalize()])

    return suggestions


class SpellcheckResource(superdesk.Resource):

    resource_methods = ['POST']
    item_methods = []

    schema = {
        'word': {'type': 'string', 'required': True},
        'language_id': {'type': 'string', 'required': True},
        'corrections': {'type': 'list'},
    }

    # you should be able to make edits
    privileges = {'POST': 'archive'}


class SpellcheckService(superdesk.Service):

    def suggest(self, word, lang):
        """Suggest corrections for given word and language.

        :param word: word that is probably wrong
        :param lang: language code
        """
        model = superdesk.get_resource_service('dictionaries').get_model_for_lang(lang)
        return norvig_suggest(word, model)

    def create(self, docs, **kwargs):
        for doc in docs:
            doc['corrections'] = self.suggest(doc['word'], doc['language_id'])
        return [doc['word'] for doc in docs]
