"""
Tests for graph algorithms (src/algorithms.py).
Each test builds a small graph and checks the algorithm output.
Run:  python -m pytest tests/
"""

import unittest
from src.graph import DirectedGraph
from src.algorithms import (
    dfs_finish_order,
    kosaraju_scc,
    condense_graph,
    topological_sort,
    find_hubs,
    pagerank,
)


# ── Helper to build graphs quickly ──────────────────────────────────

def make_graph(edges):
    """Build a DirectedGraph from a list of (src, dst) tuples."""
    g = DirectedGraph()
    for src, dst in edges:
        g.add_edge(src, dst)
    return g


# ====================================================================
# DFS
# ====================================================================

class TestDFS(unittest.TestCase):

    def test_dfs_visits_all_reachable_nodes(self):
        g = make_graph([("A", "B"), ("B", "C")])
        visited = set()
        result = dfs_finish_order(g, "A", visited)
        self.assertEqual(set(result), {"A", "B", "C"})

    def test_dfs_finish_order_leaf_finishes_first(self):
        # A -> B -> C   (C finishes first, then B, then A)
        g = make_graph([("A", "B"), ("B", "C")])
        visited = set()
        result = dfs_finish_order(g, "A", visited)
        self.assertEqual(result.index("C"), 0)  # C finishes first
        self.assertEqual(result.index("A"), 2)  # A finishes last


# ====================================================================
# Kosaraju SCC
# ====================================================================

class TestKosarajuSCC(unittest.TestCase):

    def test_no_cycle_all_singletons(self):
        # A -> B -> C  (no cycles, each node is its own SCC)
        g = make_graph([("A", "B"), ("B", "C")])
        sccs = kosaraju_scc(g)
        self.assertEqual(len(sccs), 3)
        for scc in sccs:
            self.assertEqual(len(scc), 1)

    def test_simple_cycle(self):
        # A -> B -> A  (A and B form one SCC)
        g = make_graph([("A", "B"), ("B", "A")])
        sccs = kosaraju_scc(g)
        self.assertEqual(len(sccs), 1)
        self.assertEqual(sorted(sccs[0]), ["A", "B"])

    def test_two_sccs(self):
        # Cycle: A <-> B,  and separate node C linked from B
        #   A -> B -> A  (SCC 1)
        #   B -> C       (C is its own SCC)
        g = make_graph([("A", "B"), ("B", "A"), ("B", "C")])
        sccs = kosaraju_scc(g)
        self.assertEqual(len(sccs), 2)
        # Largest SCC first
        self.assertEqual(sorted(sccs[0]), ["A", "B"])
        self.assertEqual(sccs[1], ["C"])

    def test_large_cycle(self):
        # A -> B -> C -> D -> A  (all 4 in one SCC)
        g = make_graph([("A", "B"), ("B", "C"), ("C", "D"), ("D", "A")])
        sccs = kosaraju_scc(g)
        self.assertEqual(len(sccs), 1)
        self.assertEqual(sorted(sccs[0]), ["A", "B", "C", "D"])

    def test_single_node(self):
        g = DirectedGraph()
        g.add_node("X")
        sccs = kosaraju_scc(g)
        self.assertEqual(len(sccs), 1)
        self.assertEqual(sccs[0], ["X"])


# ====================================================================
# Condensation + Topological Sort
# ====================================================================

class TestCondensationAndTopoSort(unittest.TestCase):

    def test_condensation_merges_scc(self):
        # A <-> B -> C
        g = make_graph([("A", "B"), ("B", "A"), ("B", "C")])
        sccs = kosaraju_scc(g)
        node_to_scc, dag = condense_graph(g, sccs)

        # A and B should map to the same SCC
        self.assertEqual(node_to_scc["A"], node_to_scc["B"])
        # C should be in a different SCC
        self.assertNotEqual(node_to_scc["A"], node_to_scc["C"])
        # DAG should have 2 super-nodes
        self.assertEqual(dag.num_nodes(), 2)

    def test_topo_sort_covers_all_nodes(self):
        # A -> B -> C  (each is its own SCC, DAG = 3 nodes)
        g = make_graph([("A", "B"), ("B", "C")])
        sccs = kosaraju_scc(g)
        _, dag = condense_graph(g, sccs)
        order = topological_sort(dag)
        self.assertEqual(len(order), dag.num_nodes())

    def test_topo_sort_respects_edge_direction(self):
        # A -> B -> C  (topo order must have A before B before C)
        g = make_graph([("A", "B"), ("B", "C")])
        sccs = kosaraju_scc(g)
        node_to_scc, dag = condense_graph(g, sccs)
        order = topological_sort(dag)

        scc_a = f"SCC_{node_to_scc['A']}"
        scc_b = f"SCC_{node_to_scc['B']}"
        scc_c = f"SCC_{node_to_scc['C']}"
        self.assertLess(order.index(scc_a), order.index(scc_b))
        self.assertLess(order.index(scc_b), order.index(scc_c))


# ====================================================================
# Hub Pages
# ====================================================================

class TestFindHubs(unittest.TestCase):

    def test_highest_in_degree_first(self):
        # A -> C, B -> C, D -> C   =>  C has in-degree 3
        g = make_graph([("A", "C"), ("B", "C"), ("D", "C")])
        hubs = find_hubs(g, top_n=1)
        self.assertEqual(hubs[0][0], "C")
        self.assertEqual(hubs[0][1], 3)

    def test_top_n_limits_results(self):
        g = make_graph([("A", "B"), ("A", "C"), ("A", "D")])
        hubs = find_hubs(g, top_n=2)
        self.assertEqual(len(hubs), 2)

    def test_tie_returns_all(self):
        # A -> B, C -> D  =>  B and D both have in-degree 1
        g = make_graph([("A", "B"), ("C", "D")])
        hubs = find_hubs(g, top_n=4)
        self.assertEqual(len(hubs), 4)


# ====================================================================
# PageRank
# ====================================================================

class TestPageRank(unittest.TestCase):

    def test_scores_sum_to_one(self):
        g = make_graph([("A", "B"), ("B", "C"), ("C", "A")])
        pr = pagerank(g)
        total = sum(pr.values())
        self.assertAlmostEqual(total, 1.0, places=5)

    def test_symmetric_graph_equal_ranks(self):
        # A -> B -> C -> A  (symmetric cycle, all ranks should be equal)
        g = make_graph([("A", "B"), ("B", "C"), ("C", "A")])
        pr = pagerank(g)
        values = list(pr.values())
        for v in values:
            self.assertAlmostEqual(v, values[0], places=5)

    def test_sink_node_handled(self):
        # A -> B,  B is dangling (no outgoing links)
        g = make_graph([("A", "B")])
        pr = pagerank(g)
        # Should not crash; B should have higher rank (it receives a link)
        self.assertGreater(pr["B"], pr["A"])

    def test_empty_graph(self):
        g = DirectedGraph()
        pr = pagerank(g)
        self.assertEqual(pr, {})

    def test_single_node(self):
        g = DirectedGraph()
        g.add_node("X")
        pr = pagerank(g)
        self.assertAlmostEqual(pr["X"], 1.0, places=5)


if __name__ == "__main__":
    unittest.main()
