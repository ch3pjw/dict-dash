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
from collections import defaultdict, namedtuple

Node = namedtuple('Node', ('value', 'parent'))


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


def cache(func):
    '''Decorator to provide simple non-expiring result caching to a function'''

    @wraps(func)
    def wrapped(*args, **kwargs):
        # Note: Python does not have a built in frozendict. In production, I'd
        # use something like pyrsistent.map to make the intermediate wil data
        # structure hashable and therefore safely cacheable, but for this code,
        # I'm just going to pass in kwargs that I know won't change.
        cache_key = args
        try:
            return wrapped._results_by_args[cache_key]
        except KeyError:
            result = func(*args, **kwargs)
            wrapped._results_by_args[cache_key] = result
            return result
    # Hook to allow us to reset the cache for unit testing:
    wrapped._results_by_args = {}
    return wrapped


@cache
def find_similar_words(word, index, wil):
    '''Finds all the words (using our pre-built structure) who's index-th
    letter *only* is different from the given word.
    '''
    indexes = filter(lambda i: i != index, range(len(word)))
    return set.intersection(*(wil[i][word[i]] for i in indexes)) - {word}


def generate_next_leaf_nodes(nodes, used_words, wil):
    '''Lazily produces new tree nodes that are evolved from the current leaf
    nodes.
    '''
    # Note: We can filter out words that we've previously used from the similar
    # words, because any (newer) solution evolved from the used word would by
    # definition be longer than the one containing the original use of the
    # word.
    # Note: Filtering benchmarked quicker than set difference
    for node in nodes:
        for i, letter in enumerate(node.value):
            similar_words = find_similar_words(node.value, i, wil=wil)
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


def main(word_file, stdout, stderr):
    words, pairs = parse_input(word_file)
    wil = build_words_by_indexed_letter(words)
    failed = False
    for pair in pairs:
        try:
            solution = find_shortest_solution(*pair, wil=wil)
        except ValueError as e:
            print(e.args[0], file=stderr)
            print(-1, file=stdout)
            failed = True
        else:
            print(' -> '.join(solution), file=stderr)
            print(len(solution) - 1, file=stdout)
    return failed


if __name__ == '__main__':
    failed = main(sys.stdin, sys.stdout, sys.stderr)
    if failed:
        sys.exit('Did not find solutions to all word pairs')

# =============================================================================
# Test code


from unittest import TestCase
from io import StringIO
import re


def load_word_data():
    regex = re.compile('^[a-z]{4}$')
    with open('/usr/share/dict/words') as word_file:
        # In production code, this list would be locked down to provide
        # absolute control over tests
        four_letter_words = filter(
            regex.match, map(str.strip, word_file.readlines()))
    return tuple(four_letter_words)


class TestDictionaryDash(TestCase):
    words = None
    wil = None

    def setUp(self):
        if not self.words:
            # Can't define these at class level up-front, as there is no word
            # data on the HackerRangk server, which precludes loading it at
            # definition time. Also, loading at definition time is not great
            # anyway.
            self.__class__.words = load_word_data()
            self.__class__.wil = build_words_by_indexed_letter(
                self.words)
        self.example_in_file = StringIO(
            '6\n'
            'cog\n'
            'dog\n'
            'dot\n'
            'hit\n'
            'hot\n'
            'log\n'
            '2\n'
            'hot\n'
            'dog\n'
            'hit\n'
            'cog\n')
        find_similar_words._results_by_args = {}

    def test_parse_input(self):
        expected = (
            frozenset(('cog', 'dog', 'dot', 'hit', 'hot', 'log')),
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
            # In the interests of time and brevity, only test the first three
            self.assertEqual(result[i], expected[i])

    def test_similar_words(self):
        similar_words = find_similar_words('help', 3, wil=self.wil)
        self.assertEqual(similar_words, {'held', 'hell', 'helm'})

    def test_simple_ladder(self):
        solution = find_shortest_solution('helm', 'help', self.wil)
        self.assertEqual(solution, ('helm', 'help'))

    def test_reverse_problem_len_equal(self):
        rungs_a = find_shortest_solution('bean', 'barn', self.wil)
        rungs_b = find_shortest_solution('barn', 'bean', self.wil)
        self.assertEqual(len(rungs_a), len(rungs_b))

    def test_no_solution(self):
        words = frozenset(('cog', 'dog', 'hit', 'hot', 'log'))
        wil = build_words_by_indexed_letter(words)
        self.assertRaisesRegex(
            ValueError, 'No solution.*hot.*dog', find_shortest_solution, 'hot',
            'dog', wil)

    def test_main_success(self):
        stdout = StringIO()
        stderr = StringIO()
        failed = main(self.example_in_file, stdout, stderr)
        self.assertFalse(failed)
        self.assertEqual(stdout.getvalue(), '2\n4\n')
        self.assertEqual(
            stderr.getvalue(),
            'hot -> dot -> dog\nhit -> hot -> dot -> dog -> cog\n')

    def test_main_failure(self):
        stdin = StringIO('1\nword\n1\nword\ngone\n')
        stdout = StringIO()
        stderr = StringIO()
        failed = main(stdin, stdout, stderr)
        self.assertTrue(failed)
        self.assertEqual(stdout.getvalue(), '-1\n')


# =============================================================================
# Personal notes
#
# How did you approach the problem?
#
#   I'm presuming that you're interested in the thought processes that led me
#   to my submitted solution. Apologies if this is a wild tangent!
#
#   My first thoughts were along the lines of "I need to explore the possible
#   space of solutions efficiently. What constraints do I have?". I quickly
#   started trying to index the word list, as I knew I would need to search it
#   efficiently. Although I hadn't got the whole shape of the code in my head
#   at that point, I used that data structure to spark thoughts about what kind
#   of actions my searching would endtail.
#
#   My initial solution was just to build up a kind of "meta word ladder", in
#   which every rung contained the set of all possibilities that extended out
#   from the rung preceding it. That gave me the right answers in the sample
#   case, but I was nervous about not being able to prove the correctness of
#   the answer without an actual chain/evolution history. Also, I wanted to see
#   the chain on stderr, because that was kinda fun.
#
#   One idea I'd had whilst writing that initial solution was to build a graph
#   of all of the possible single-letter changes between words. I'd discounted
#   it because it felt like generating the structure was harder/more wasteful
#   than solving the problem, but came back to it as I wanted the whole chain
#   as part of the solution. That idea evolved into generating the graph lazily
#   and bailing when I found a solution.
#
#   Once the shape had settled to something that worked and didn't seem to
#   wasteful, I set about cleaning up, adding some more tests and optimising.
#
#
# How did you check that your solution is correct and efficient?
#
#   I wrote most of the test code as I was assembling the various layers of
#   functionality (file parser, indexed word structure, similar word generation
#   and so on), verifying as I went that my code was behaving as intended.  I
#   didn't strictly or comprehensively TDD it, as I was playing around with
#   various nascent ideas in tandem with shaping the code and testing it.
#
#   I struggled a bit knowing how to prove overall correctness, as I kinda
#   needed a correct implementation to run against to generate test cases! I
#   settled for corroborating a few solutions against online word ladder
#   generators, adjusting for words missing from my system's dict file, and
#   enshrining a couple of word ladders in unit tests.
#
#   For profiling, I just used output from python cProfile and ipython %prun
#   to find bottlenecks and executed bits of my code or trial functions to test
#   the speed of potential optimisations. I made sure I'd got test coverage of
#   correct code before optimising! Some optimisation of my early code
#   included:
#    - Noting that find_similar_words was by far the bottle kneck and
#      optimising with a call to set.intersection that pushed a lot of the set
#      manipulation into the C.
#    - Caching the results for similar words, so subsequent runs didn't use the
#      computationally heavy code again.
#    - Turning generate_next_leaf_nodes into an actual generator function, so
#      that we didn't pre-compute too many possibilities before cutting short
#      once we'd found a solution.
#    - Checking that a filter was quicker than computing a set difference
#
#   To tidy up, I ran the unittest with coverage and plugged any gaps (mostly
#   main). The coverage report says 100%, but that *must* be dodgy, because
#   under nosetests it won't be executing the statements inside the
#   `if __name__ == '__main__'` conditional. I've seen this problem on my
#   machine before, but don't have time to debug the coverage tool.
#
# Assumptions:
#
# I've tried to state assumptions through the actual code. The biggest
# assumption I've made is that the breadth first search is the best/only way to
# go about generating a good solution.
#
# There are a whole bunch of problems that can arise from bad input
# (non-lower-case-ASCII chars, mixed word lengths, duplicated words, pairs that
# reference non-dict words and so on), but that clutters readability for the
# example case and doesn't seem to be a core part of the problem, so this code
# just assumes the input is good. Also, I think in the listed cases, this code
# would still handle things reasonably well.
