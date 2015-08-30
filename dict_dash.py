import sys
from collections import defaultdict, namedtuple

Node = namedtuple('Node', ('value', 'parent'))


def parse_input(f):
    'Parses the stdin data from hackerrank, assuming input is correct'
    get = lambda: f.readline().strip()
    num_words = int(get())
    words = frozenset(get() for _ in range(num_words))
    num_pairs = int(get())
    pairs = tuple((get(), get()) for _ in range(num_pairs))
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


def generate_next_rung(nodes, used_words, wli):
    new_nodes = []
    for node in nodes:
        for i, letter in enumerate(node.value):
            similar_words = find_similar_words(node.value, i, wli)
            new_nodes.extend(map(
                lambda sw: Node(sw, parent=node),
                filter(lambda sw: sw not in used_words, similar_words)))
    return new_nodes


def flatten_solution_node(node):
    yield node.value
    while node.parent:
        node = node.parent
        yield node.value


def generate_shortest_solution(start, end, wli):
    rungs = [{Node(start, parent=None)}]
    used_words = {start}
    solution = None
    while not solution:
        next_rung_nodes = generate_next_rung(rungs[-1], used_words, wli)
        if not next_rung_nodes:
            raise ValueError(
                'No solutions for {!r} -> {!r}'.format(start, end))
        used_words.update(map(lambda n: n.value, next_rung_nodes))
        for node in next_rung_nodes:
            if node.value == end:
                return tuple(reversed(tuple(flatten_solution_node(node))))
        else:
            rungs.append(next_rung_nodes)


def main(word_file):
    words, pairs = parse_input(word_file)
    wli = get_words_by_letter_and_index(words)
    for pair in pairs:
        try:
            solution = generate_shortest_solution(*pair, wli=wli)
        except ValueError as e:
            print(e.args[0], sys.stderr)
        else:
            print(' -> '.join(solution), file=sys.stderr)
            print(len(solution) - 1)


if __name__ == '__main__':
    main(sys.stdin)


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
            self.words_by_letter_and_index = get_words_by_letter_and_index(
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

    def test_simple_ladder(self):
        solution = generate_shortest_solution(
            'hell', 'help', self.words_by_letter_and_index)
        self.assertEqual(solution, ('hell', 'help'))

    def test_reverse_problem_len_equal(self):
        rungs_a = generate_shortest_solution(
            'bean', 'barn', self.words_by_letter_and_index)
        rungs_b = generate_shortest_solution(
            'barn', 'bean', self.words_by_letter_and_index)
        self.assertEqual(len(rungs_a), len(rungs_b))
