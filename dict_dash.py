from collections import defaultdict


def parse_input(f):
    'Parses the stdin data from hackerrank, assuming input is correct'
    get = lambda: f.readline().strip()
    num_words = int(get())
    words = frozenset(get() for _ in range(num_words))
    num_pairs = int(get())
    pairs = frozenset((get(), get()) for _ in range(num_pairs))
    return words, pairs


def get_words_by_letter_and_index(words):
    words_by_letter_and_index = defaultdict(lambda: defaultdict(set))
    for word in words:
        for i, letter in enumerate(word):
            words_by_letter_and_index[i][letter].add(word)
    return words_by_letter_and_index


def find_similar_words(word, index, words_by_letter_and_index):
    '''Finds all the words in our structured data who's index-th letter only is
    different from the given word
    '''
    similar_words = None  # FIXME: not so nice
    indexes = filter(lambda i: i != index, range(len(word)))
    for i in indexes:
        considered_words = words_by_letter_and_index[i][word[i]]
        if similar_words is None:
            similar_words = considered_words - {word}
        else:
            similar_words &= considered_words
    return similar_words


def generate_next_rung(words, used_words, wli):
    new_words = set()
    for word in words:
        for i, letter in enumerate(word):
            new_words |= find_similar_words(word, i, wli)
    return new_words - used_words


def generate_solutions(start, end, words):
    wli = get_words_by_letter_and_index(words)
    rungs = [{start}]
    used_words = {start}
    while end not in rungs[-1]:
        next_rung = generate_next_rung(rungs[-1], used_words, wli)
        if not next_rung:
            raise ValueError(
                'No solutions for {!r} -> {!r}'.format(start, end))
        used_words |= next_rung
        rungs.append(next_rung)
    return rungs


from unittest import TestCase
from io import StringIO
import re


def load_word_data():
    regex = re.compile('^[a-z]{4}$')
    with open('/usr/share/dict/words') as word_file:
        # Caution: this list should be locked down in 'production' tests!
        four_letter_words = filter(
            regex.match, map(str.strip, word_file.readlines()))
    return tuple(four_letter_words)


class TestDictionaryDash(TestCase):
    def test_parse_input(self):
        in_file = StringIO(
            '7\n'
            'cog\n'
            'dog\n'
            'dot\n'
            'hit\n'
            'hot\n'
            'log\n'
            'lot\n'
            '2\n'
            'hot\n'
            'dog\n'
            'hit\n'
            'cog\n')
        expected = (
            frozenset(('cog', 'dog', 'dot', 'hit', 'hot', 'log', 'lot')),
            frozenset((('hot', 'dog'), ('hit', 'cog'))),
        )
        self.assertEqual(parse_input(in_file), expected)

    def test_words_by_letter_and_index(self):
        words = 'acceded', 'agisted', 'biscuit', 'cellist', 'firemen'
        expected = {
            0: {'a': {'acceded', 'agisted'},
                'b': {'biscuit'},
                'c': {'cellist'},
                'f': {'firemen'}},
            1: {'c': {'acceded'},
                'g': {'agisted'},
                'i': {'biscuit', 'firemen'},
                'e': {'cellist'}},
            2: {'c': {'acceded'},
                'i': {'agisted'},
                's': {'biscuit'},
                'l': {'cellist'},
                'r': {'firemen'}}}
        result = get_words_by_letter_and_index(words)
        self.assertEqual(len(result), 7)
        for i in range(3):
            # In the interests of time and brevity
            self.assertEqual(result[i], expected[i])

    def test_similar_words(self):
        four_letter_words = load_word_data()
        wli = get_words_by_letter_and_index(four_letter_words)
        similar_words = find_similar_words('help', 3, wli)
        self.assertEqual(similar_words, {'held', 'hell', 'helm'})

    def test_ladder(self):
        words = load_word_data()
        rungs = generate_solutions('hell', 'help', words)
        self.assertEqual(len(rungs), 2)
        self.assertIn('hell', rungs[0])
        self.assertIn('help', rungs[1])

    def test_bean_barn(self):
        words = load_word_data()
        rungs_a = generate_solutions('bean', 'barn', words)
        rungs_b = generate_solutions('barn', 'bean', words)
        self.assertEqual(len(rungs_a), len(rungs_b))
