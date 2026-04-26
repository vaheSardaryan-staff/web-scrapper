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
    dijkstra,
    reconstruct_path,
    hits,
    floyd_warshall,
    graph_diameter,
    reconstruct_fw_path,
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


# ====================================================================
# Dijkstra's Shortest Path
# ====================================================================

class TestDijkstra(unittest.TestCase):

    def test_shortest_path_simple_chain(self):
        # A -1-> B -1-> C   shortest A->C = 2.0
        g = DirectedGraph()
        g.add_edge("A", "B", weight=1.0)
        g.add_edge("B", "C", weight=1.0)
        dist, _ = dijkstra(g, "A")
        self.assertAlmostEqual(dist["C"], 2.0)

    def test_dijkstra_prefers_cheaper_path(self):
        # A -10-> C  vs  A -1-> B -1-> C (cost 2)
        # Dijkstra must choose A->B->C
        g = DirectedGraph()
        g.add_edge("A", "C", weight=10.0)
        g.add_edge("A", "B", weight=1.0)
        g.add_edge("B", "C", weight=1.0)
        dist, prev = dijkstra(g, "A")
        self.assertAlmostEqual(dist["C"], 2.0)
        self.assertEqual(prev["C"], "B")

    def test_source_distance_is_zero(self):
        g = make_graph([("A", "B"), ("B", "C")])
        dist, _ = dijkstra(g, "A")
        self.assertEqual(dist["A"], 0.0)

    def test_unreachable_node_is_infinity(self):
        # A -> B,  C is isolated
        g = DirectedGraph()
        g.add_edge("A", "B")
        g.add_node("C")
        dist, _ = dijkstra(g, "A")
        self.assertEqual(dist["C"], float("inf"))

    def test_reconstruct_path_simple(self):
        g = DirectedGraph()
        g.add_edge("A", "B", weight=1.0)
        g.add_edge("B", "C", weight=1.0)
        _, prev = dijkstra(g, "A")
        path = reconstruct_path(prev, "A", "C")
        self.assertEqual(path, ["A", "B", "C"])

    def test_reconstruct_path_source_equals_target(self):
        g = make_graph([("A", "B")])
        _, prev = dijkstra(g, "A")
        path = reconstruct_path(prev, "A", "A")
        self.assertEqual(path, ["A"])

    def test_reconstruct_path_unreachable_returns_none(self):
        g = DirectedGraph()
        g.add_edge("A", "B")
        g.add_node("C")
        _, prev = dijkstra(g, "A")
        path = reconstruct_path(prev, "A", "C")
        self.assertIsNone(path)

    def test_dijkstra_non_obvious_cheaper_path(self):
        # Models the home->contact demo:
        # S -8-> T  (direct, expensive)
        # S -1-> M1 -1-> M2 -1-> T  (indirect, cost 3)
        g = DirectedGraph()
        g.add_edge("S", "T",  weight=8.0)
        g.add_edge("S", "M1", weight=1.0)
        g.add_edge("M1", "M2", weight=1.0)
        g.add_edge("M2", "T",  weight=1.0)
        dist, prev = dijkstra(g, "S")
        self.assertAlmostEqual(dist["T"], 3.0)
        path = reconstruct_path(prev, "S", "T")
        self.assertEqual(path, ["S", "M1", "M2", "T"])

    def test_weighted_successors_used(self):
        g = DirectedGraph()
        g.add_edge("X", "Y", weight=5.0)
        self.assertEqual(g.weighted_successors("X"), [("Y", 5.0)])
        self.assertAlmostEqual(g.get_weight("X", "Y"), 5.0)


# ====================================================================
# HITS Algorithm
# ====================================================================

class TestHITS(unittest.TestCase):

    def test_empty_graph_returns_empty(self):
        g = DirectedGraph()
        hub, auth = hits(g)
        self.assertEqual(hub, {})
        self.assertEqual(auth, {})

    def test_isolated_node_has_zero_scores(self):
        g = DirectedGraph()
        g.add_node("X")
        hub, auth = hits(g)
        self.assertAlmostEqual(hub["X"],  0.0, places=5)
        self.assertAlmostEqual(auth["X"], 0.0, places=5)

    def test_chain_roles_are_distinct(self):
        # A -> B -> C
        # A should score high as hub (points to B, which points to auth C)
        # C should score high as authority (is pointed to by B which is pointed to by A)
        g = make_graph([("A", "B"), ("B", "C")])
        hub, auth = hits(g)
        self.assertGreater(hub["A"],  hub["C"])    # A is a better hub than C
        self.assertGreater(auth["C"], auth["A"])   # C is a better authority than A

    def test_hub_and_auth_are_l2_normalised(self):
        g = make_graph([("A", "B"), ("B", "C"), ("C", "A")])
        hub, auth = hits(g)
        hub_norm  = sum(v * v for v in hub.values())  ** 0.5
        auth_norm = sum(v * v for v in auth.values()) ** 0.5
        self.assertAlmostEqual(hub_norm,  1.0, places=4)
        self.assertAlmostEqual(auth_norm, 1.0, places=4)

    def test_mutual_link_symmetric(self):
        # A <-> B — symmetric graph, both should have equal scores
        g = make_graph([("A", "B"), ("B", "A")])
        hub, auth = hits(g)
        self.assertAlmostEqual(hub["A"],  hub["B"],  places=4)
        self.assertAlmostEqual(auth["A"], auth["B"], places=4)


# ====================================================================
# Floyd-Warshall All-Pairs Shortest Path
# ====================================================================

class TestFloydWarshall(unittest.TestCase):

    def test_direct_edge_distance(self):
        g = DirectedGraph()
        g.add_edge("A", "B", weight=3.0)
        dist, _ = floyd_warshall(g)
        self.assertAlmostEqual(dist["A"]["B"], 3.0)

    def test_indirect_path(self):
        # A -1-> B -2-> C   dist A->C = 3
        g = DirectedGraph()
        g.add_edge("A", "B", weight=1.0)
        g.add_edge("B", "C", weight=2.0)
        dist, _ = floyd_warshall(g)
        self.assertAlmostEqual(dist["A"]["C"], 3.0)

    def test_shortest_over_direct_edge(self):
        # A -10-> C  vs  A -1-> B -1-> C
        g = DirectedGraph()
        g.add_edge("A", "C", weight=10.0)
        g.add_edge("A", "B", weight=1.0)
        g.add_edge("B", "C", weight=1.0)
        dist, _ = floyd_warshall(g)
        self.assertAlmostEqual(dist["A"]["C"], 2.0)

    def test_unreachable_is_infinity(self):
        g = DirectedGraph()
        g.add_edge("A", "B")
        g.add_node("C")
        dist, _ = floyd_warshall(g)
        self.assertEqual(dist["A"]["C"], float("inf"))

    def test_self_distance_is_zero(self):
        g = make_graph([("A", "B"), ("B", "C")])
        dist, _ = floyd_warshall(g)
        for n in g.nodes():
            self.assertEqual(dist[n][n], 0.0)

    def test_empty_graph(self):
        g = DirectedGraph()
        dist, nh = floyd_warshall(g)
        self.assertEqual(dist, {})
        self.assertEqual(nh,   {})

    def test_graph_diameter(self):
        # A -1-> B -2-> C   diameter = 3 (A to C)
        g = DirectedGraph()
        g.add_edge("A", "B", weight=1.0)
        g.add_edge("B", "C", weight=2.0)
        dist, _ = floyd_warshall(g)
        diam, src, dst = graph_diameter(dist)
        self.assertAlmostEqual(diam, 3.0)
        self.assertEqual(src, "A")
        self.assertEqual(dst, "C")

    def test_reconstruct_fw_path(self):
        g = DirectedGraph()
        g.add_edge("A", "B", weight=1.0)
        g.add_edge("B", "C", weight=1.0)
        _, nh = floyd_warshall(g)
        path = reconstruct_fw_path(nh, "A", "C")
        self.assertEqual(path, ["A", "B", "C"])

    def test_reconstruct_fw_path_unreachable(self):
        g = DirectedGraph()
        g.add_edge("A", "B")
        g.add_node("C")
        _, nh = floyd_warshall(g)
        path = reconstruct_fw_path(nh, "A", "C")
        self.assertIsNone(path)


if __name__ == "__main__":
    unittest.main()
