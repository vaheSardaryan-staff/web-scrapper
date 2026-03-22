"""
graph.py
--------
Directed graph implemented as an adjacency list.
Supports all operations needed by the crawler and analysis algorithms.
"""

from collections import defaultdict


class DirectedGraph:
    """
    Adjacency-list directed graph.

    Internally we store:
        _adj  : node -> list of successor nodes  (forward edges)
        _radj : node -> list of predecessor nodes (reverse edges, for Kosaraju)
    """

    def __init__(self):
        self._adj  = defaultdict(list)   # forward edges
        self._radj = defaultdict(list)   # reverse edges
        self._nodes = set()

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def add_node(self, node: str):
        """Register a node even if it has no edges."""
        self._nodes.add(node)
        # Make sure the node appears in both dicts (even with empty lists)
        _ = self._adj[node]
        _ = self._radj[node]

    def add_edge(self, src: str, dst: str):
        """Add a directed edge src -> dst (self-loops are stored but noted)."""
        self.add_node(src)
        self.add_node(dst)
        if dst not in self._adj[src]:        # avoid duplicate edges
            self._adj[src].append(dst)
            self._radj[dst].append(src)

    # ------------------------------------------------------------------
    # Basic queries
    # ------------------------------------------------------------------

    def nodes(self):
        return list(self._nodes)

    def successors(self, node: str):
        return list(self._adj[node])

    def predecessors(self, node: str):
        return list(self._radj[node])

    def in_degree(self, node: str) -> int:
        return len(self._radj[node])

    def out_degree(self, node: str) -> int:
        return len(self._adj[node])

    def all_in_degrees(self) -> dict:
        """Return {node: in_degree} for every node."""
        return {n: self.in_degree(n) for n in self._nodes}

    def num_nodes(self) -> int:
        return len(self._nodes)

    def num_edges(self) -> int:
        return sum(len(nbrs) for nbrs in self._adj.values())

    def is_dangling(self, node: str) -> bool:
        """A dangling page has no outgoing links."""
        return self.out_degree(node) == 0

    def dangling_nodes(self) -> list:
        return [n for n in self._nodes if self.is_dangling(n)]

    def self_loops(self) -> list:
        """Return list of nodes with self-loops."""
        return [n for n in self._nodes if n in self._adj[n]]

    # ------------------------------------------------------------------
    # Reverse graph (used by Kosaraju's second pass)
    # ------------------------------------------------------------------

    def reverse(self) -> "DirectedGraph":
        """Return a new graph with all edges flipped."""
        g = DirectedGraph()
        for node in self._nodes:
            g.add_node(node)
        for src in self._nodes:
            for dst in self._adj[src]:
                g.add_edge(dst, src)
        return g

    # ------------------------------------------------------------------
    # String representation
    # ------------------------------------------------------------------

    def __repr__(self):
        lines = [f"DirectedGraph ({self.num_nodes()} nodes, {self.num_edges()} edges)"]
        for node in sorted(self._nodes):
            nbrs = ", ".join(sorted(self._adj[node])) or "∅"
            lines.append(f"  {node} -> [{nbrs}]")
        return "\n".join(lines)
