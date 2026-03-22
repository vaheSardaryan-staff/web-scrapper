"""
Tests for DirectedGraph (src/graph.py).
Run:  python -m pytest tests/
"""

import unittest
from src.graph import DirectedGraph


class TestAddNodeAndEdge(unittest.TestCase):
    """Basic graph construction."""

    def test_add_single_node(self):
        g = DirectedGraph()
        g.add_node("A")
        self.assertIn("A", g.nodes())
        self.assertEqual(g.num_nodes(), 1)
        self.assertEqual(g.num_edges(), 0)

    def test_add_edge_creates_both_nodes(self):
        g = DirectedGraph()
        g.add_edge("A", "B")
        self.assertIn("A", g.nodes())
        self.assertIn("B", g.nodes())
        self.assertEqual(g.num_nodes(), 2)
        self.assertEqual(g.num_edges(), 1)

    def test_duplicate_edge_ignored(self):
        g = DirectedGraph()
        g.add_edge("A", "B")
        g.add_edge("A", "B")  # duplicate
        self.assertEqual(g.num_edges(), 1)

    def test_multiple_edges(self):
        g = DirectedGraph()
        g.add_edge("A", "B")
        g.add_edge("A", "C")
        g.add_edge("B", "C")
        self.assertEqual(g.num_edges(), 3)


class TestDegrees(unittest.TestCase):
    """In-degree and out-degree queries."""

    def setUp(self):
        #   A -> B -> C
        #   A -> C
        self.g = DirectedGraph()
        self.g.add_edge("A", "B")
        self.g.add_edge("A", "C")
        self.g.add_edge("B", "C")

    def test_out_degree(self):
        self.assertEqual(self.g.out_degree("A"), 2)  # A -> B, A -> C
        self.assertEqual(self.g.out_degree("B"), 1)  # B -> C
        self.assertEqual(self.g.out_degree("C"), 0)  # C has no outgoing

    def test_in_degree(self):
        self.assertEqual(self.g.in_degree("A"), 0)  # nobody links to A
        self.assertEqual(self.g.in_degree("B"), 1)  # A -> B
        self.assertEqual(self.g.in_degree("C"), 2)  # A -> C, B -> C

    def test_all_in_degrees(self):
        degrees = self.g.all_in_degrees()
        self.assertEqual(degrees["A"], 0)
        self.assertEqual(degrees["C"], 2)


class TestSuccessorsAndPredecessors(unittest.TestCase):

    def test_successors(self):
        g = DirectedGraph()
        g.add_edge("A", "B")
        g.add_edge("A", "C")
        self.assertEqual(sorted(g.successors("A")), ["B", "C"])

    def test_predecessors(self):
        g = DirectedGraph()
        g.add_edge("A", "C")
        g.add_edge("B", "C")
        self.assertEqual(sorted(g.predecessors("C")), ["A", "B"])


class TestDanglingNodes(unittest.TestCase):

    def test_node_with_no_outgoing_is_dangling(self):
        g = DirectedGraph()
        g.add_edge("A", "B")
        # B has no outgoing edges
        self.assertTrue(g.is_dangling("B"))
        self.assertFalse(g.is_dangling("A"))

    def test_dangling_nodes_list(self):
        g = DirectedGraph()
        g.add_edge("A", "B")
        g.add_edge("A", "C")
        # B and C are dangling
        self.assertEqual(sorted(g.dangling_nodes()), ["B", "C"])


class TestSelfLoops(unittest.TestCase):

    def test_self_loop_detected(self):
        g = DirectedGraph()
        g.add_edge("A", "A")  # self-loop
        self.assertIn("A", g.self_loops())

    def test_no_self_loop(self):
        g = DirectedGraph()
        g.add_edge("A", "B")
        self.assertEqual(g.self_loops(), [])


class TestReverse(unittest.TestCase):

    def test_reverse_flips_edges(self):
        g = DirectedGraph()
        g.add_edge("A", "B")
        g.add_edge("B", "C")

        rev = g.reverse()
        # In reversed graph: B -> A, C -> B
        self.assertIn("A", rev.successors("B"))
        self.assertIn("B", rev.successors("C"))
        # A should have no outgoing edges in reversed graph
        self.assertEqual(rev.successors("A"), [])

    def test_reverse_preserves_node_count(self):
        g = DirectedGraph()
        g.add_edge("A", "B")
        g.add_node("C")  # isolated node
        rev = g.reverse()
        self.assertEqual(rev.num_nodes(), 3)


class TestRepr(unittest.TestCase):

    def test_repr_not_empty(self):
        g = DirectedGraph()
        g.add_edge("A", "B")
        text = repr(g)
        self.assertIn("DirectedGraph", text)
        self.assertIn("A", text)


if __name__ == "__main__":
    unittest.main()
