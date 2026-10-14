"""One moved row must produce one question, even in a long backlog."""
import importlib.util
import unittest
from test_public import SCRIPT

spec = importlib.util.spec_from_file_location('inwoven_reorder', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ReorderTests(unittest.TestCase):
    def test_twenty_row_moves_both_ways_and_swap(self):
        ids = ['K' + str(n) for n in range(100, 120)]
        def text(order):
            return '| Item (PBI) | Core Job | Context | Status | Driver |\n|---|---|---|---|---|\n' + ''.join('| ' + i + '. Item | | | | |\n' for i in order)
        for order, moved in ((ids[1:] + ids[:1], 'K100'), (ids[-1:] + ids[:-1], 'K119'),
                             ([ids[1], ids[0]] + ids[2:], 'K101')):
            questions = module.reminder(text(ids), text(order))
            self.assertEqual(questions, ['Did the person ask in this conversation for ' + moved + ' to be reordered? If not, undo it now.'])
