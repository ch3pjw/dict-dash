#!/usr/bin/env python3
'''
Solves the HackerRank/Improbable "Dictionary Dash" problem.

The general approach is to evolve a tree of possible solutions growing from the
starting word by iteratively adding "similar words" (one letter different)
breadth-first to the tree's leaf nodes. We stop adding to the tree as soon as
we have added the end word and return the lineage of that node as the shortest
solution. If at any point we have no more words to add to the tree, yet still
have not reached the target word, we know we cannot find a solution and
therefore raise an error.

Tests and personal notes included after the code
'''

import sys
from functools import wraps
from itertools import starmap
from collections import defaultdict, namedtuple

Node = namedtuple('Node', ('value', 'parent'))


def cache(func):
    '''Decorator to provide simple non-expiring result caching to a function'''
    results_by_args = {}

    @wraps(func)
    def wrapped(*args, **kwargs):
        # Note: Python does not have a built in frozendict. In production, I'd
        # use something like pyrsistent.map to make the intermediate data
        # structure hashable and therefore safely cacheable, but for this,
        # we'll just check the IDs in the kwargs, pass mutables by keyword and
        # trust the caller not to change them.
        kwarg_ids = frozenset(starmap(lambda k, v: (k, id(v)), kwargs.items()))
        cache_key = args, kwarg_ids
        try:
            return results_by_args[cache_key]
        except KeyError:
            result = func(*args, **kwargs)
            results_by_args[cache_key] = result
            return result
    return wrapped


def parse_input(f):
    '''Parses the stdin data, assuming input is correct'''
    get = lambda: f.readline().strip()
    num_words = int(get())
    words = frozenset(get() for _ in range(num_words))
    num_pairs = int(get())
    # The order of pairs is important for output correlation with input:
    pairs = tuple((get(), get()) for _ in range(num_pairs))
    return words, pairs


def build_words_by_indexed_letter(words):
    '''Returns a structure of nested dicts keyed by letter index then letter,
    mapping these to sets such that we can quickly find the set of all words
    that have a given letter in a given position.

    We hereafter refer to the "words by indexed letters" structure by the
    acronym 'wil' for brevity.
    '''
    wil = defaultdict(lambda: defaultdict(set))
    for word in words:
        for i, letter in enumerate(word):
            wil[i][letter].add(word)
    return wil


@cache
def find_similar_words(word, index, wil):
    '''Finds all the words (using our pre-built structure) who's index-th
    letter *only* is different from the given word.
    '''
    similar_words = None  # FIXME: not so nice
    indexes = filter(lambda i: i != index, range(len(word)))
    for i in indexes:
        considered_words = wil[i][word[i]]
        if similar_words is None:
            similar_words = considered_words - {word}
        else:
            similar_words &= considered_words
    return similar_words


def generate_next_leaf_nodes(nodes, used_words, wil):
    '''Lazily produces new tree nodes that are evolved from the current leaf
    nodes.
    '''
    for node in nodes:
        for i, letter in enumerate(node.value):
            similar_words = find_similar_words(
                node.value, i, wil=wil)
            yield from map(
                lambda sw: Node(sw, parent=node),
                filter(lambda sw: sw not in used_words, similar_words))


def retrace_solution(node):
    '''Backtracks the ancestry of a node from the tree, which represents a
    soltuion state.
    '''
    yield node.value
    while node.parent:
        node = node.parent
        yield node.value


def find_shortest_solution(start_word, end_word, wil):
    used_words = {start_word}
    leaf_nodes = [Node(start_word, parent=None)]
    while True:
        next_leaf_nodes = []
        for node in generate_next_leaf_nodes(leaf_nodes, used_words, wil):
            if node.value == end_word:
                return tuple(reversed(tuple(retrace_solution(node))))
            else:
                next_leaf_nodes.append(node)
                used_words.add(node.value)
        if next_leaf_nodes:
            leaf_nodes = next_leaf_nodes
        else:
            raise ValueError(
                'No solutions for {!r} -> {!r}'.format(start_word, end_word))


def main(word_file):
    words, pairs = parse_input(word_file)
    wil = build_words_by_indexed_letter(words)
    failed = False
    for pair in pairs:
        try:
            solution = find_shortest_solution(*pair, wil=wil)
        except ValueError as e:
            print(e.args[0], file=sys.stderr)
            print(-1)
            failed = True
        else:
            print(' -> '.join(solution), file=sys.stderr)
            print(len(solution) - 1)
    return failed


if __name__ == '__main__':
    failed = main(sys.stdin)
    if failed:
        sys.exit('Did not find solutions to all word pairs')



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
    words = None

    def setUp(self):
        if not self.words:
            self.words = load_word_data()
            self.wil = build_words_by_indexed_letter(
                self.words)
        self.example_in_file = StringIO(
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

    def test_parse_input(self):
        expected = (
            frozenset(('cog', 'dog', 'dot', 'hit', 'hot', 'log', 'lot')),
            tuple((('hot', 'dog'), ('hit', 'cog'))),
        )
        self.assertEqual(parse_input(self.example_in_file), expected)

    def test_words_by_indexed_letter(self):
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
        result = build_words_by_indexed_letter(words)
        self.assertEqual(len(result), 7)
        for i in range(3):
            # In the interests of time and brevity
            self.assertEqual(result[i], expected[i])

    def test_similar_words(self):
        four_letter_words = load_word_data()
        wil = build_words_by_indexed_letter(four_letter_words)
        similar_words = find_similar_words(
            'help', 3, wil=wil)
        self.assertEqual(similar_words, {'held', 'hell', 'helm'})

    def test_simple_ladder(self):
        solution = find_shortest_solution(
            'helm', 'help', self.wil)
        self.assertEqual(solution, ('helm', 'help'))

    def test_reverse_problem_len_equal(self):
        rungs_a = find_shortest_solution(
            'bean', 'barn', self.wil)
        rungs_b = find_shortest_solution(
            'barn', 'bean', self.wil)
        self.assertEqual(len(rungs_a), len(rungs_b))
