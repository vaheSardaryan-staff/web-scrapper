"""
algorithms.py
-------------
All graph algorithms used in the Web Crawler & Link Graph Analyzer:

  1. DFS                     — iterative, used internally
  2. Kosaraju's Algorithm    — Strongly Connected Components  O(V + E)
  3. Topological Sort        — on the condensed DAG           O(V + E)
  4. In-degree / Hub Pages   — O(V + E)
  5. PageRank                — simplified power-iteration     O(k * (V + E))
  6. Dijkstra's Algorithm    — single-source shortest path    O((V + E) log V)

Every function is self-contained and receives a DirectedGraph as input.
"""

import heapq
from collections import defaultdict, deque
from src.graph import DirectedGraph


# ======================================================================
# 1. ITERATIVE DFS  (helper used by Kosaraju)
# ======================================================================

def dfs_finish_order(graph: DirectedGraph, start: str, visited: set) -> list[str]:
    """
    Iterative DFS from `start`.  Returns nodes in *finish* order
    (i.e. a node appears in the list only after all its descendants finish).

    This mimics the post-order of recursive DFS without hitting Python's
    recursion limit on large graphs.

    Time  : O(V + E)
    Space : O(V)
    """
    finish_order = []
    # Stack holds (node, iterator_over_successors)
    stack = [(start, iter(graph.successors(start)))]
    visited.add(start)

    while stack:
        node, children = stack[-1]
        try:
            child = next(children)
            if child not in visited:
                visited.add(child)
                stack.append((child, iter(graph.successors(child))))
        except StopIteration:
            # All children processed — node is finished
            stack.pop()
            finish_order.append(node)

    return finish_order


# ======================================================================
# 2. KOSARAJU'S ALGORITHM — Strongly Connected Components
# ======================================================================

def kosaraju_scc(graph: DirectedGraph) -> list[list[str]]:
    """
    Kosaraju's Two-Pass SCC Algorithm.

    Pass 1 — DFS on original graph, collect finish order.
    Pass 2 — DFS on REVERSED graph in reverse finish order.
             Each DFS tree in pass 2 is one SCC.

    Returns
    -------
    List of SCCs, each SCC is a list of node names.
    SCCs are returned largest-first.

    Complexity
    ----------
    Time  : O(V + E)  — two full graph traversals
    Space : O(V + E)  — storing the reverse graph + stacks
    """
    # ── Pass 1: compute finish order on original graph ────────────────
    visited: set = set()
    finish_order: list[str] = []

    for node in graph.nodes():
        if node not in visited:
            finish_order.extend(dfs_finish_order(graph, node, visited))

    # ── Pass 2: DFS on reversed graph in reverse-finish-order ─────────
    rev_graph = graph.reverse()
    visited2: set = set()
    sccs: list[list[str]] = []

    for node in reversed(finish_order):
        if node not in visited2:
            component = dfs_finish_order(rev_graph, node, visited2)
            sccs.append(component)

    sccs.sort(key=len, reverse=True)
    return sccs


# ======================================================================
# 3. CONDENSATION DAG + TOPOLOGICAL SORT
# ======================================================================

def condense_graph(graph: DirectedGraph, sccs: list[list[str]]) -> tuple[dict, DirectedGraph]:
    """
    Build the condensation DAG:
    - Each SCC becomes a single super-node (labelled by its index).
    - An edge exists between two super-nodes if there is any edge
      between their member sets in the original graph.

    Returns
    -------
    node_to_scc : {original_node: scc_index}
    dag         : condensed DirectedGraph with nodes "SCC_0", "SCC_1", …
    """
    node_to_scc: dict[str, int] = {}
    for idx, component in enumerate(sccs):
        for node in component:
            node_to_scc[node] = idx

    dag = DirectedGraph()
    for i in range(len(sccs)):
        dag.add_node(f"SCC_{i}")

    for src in graph.nodes():
        for dst in graph.successors(src):
            src_id = node_to_scc[src]
            dst_id = node_to_scc[dst]
            if src_id != dst_id:                  # skip intra-SCC edges
                dag.add_edge(f"SCC_{src_id}", f"SCC_{dst_id}")

    return node_to_scc, dag


def topological_sort(dag: DirectedGraph) -> list[str]:
    """
    Kahn's Algorithm — BFS-based topological sort on a DAG.

    Algorithm
    ---------
    1. Compute in-degree for every node.
    2. Enqueue all nodes with in-degree 0.
    3. While queue is not empty:
       a. Dequeue node u; append to result.
       b. For each successor v: decrement in-degree(v).
          If in-degree(v) == 0: enqueue v.
    4. If result length < V: graph has a cycle (should not happen on condensed DAG).

    Time  : O(V + E)
    Space : O(V)
    """
    in_deg = dag.all_in_degrees()
    queue = deque(n for n in dag.nodes() if in_deg[n] == 0)
    order: list[str] = []

    while queue:
        node = queue.popleft()
        order.append(node)
        for nbr in dag.successors(node):
            in_deg[nbr] -= 1
            if in_deg[nbr] == 0:
                queue.append(nbr)

    return order


# ======================================================================
# 4. HUB PAGES — highest in-degree
# ======================================================================

def find_hubs(graph: DirectedGraph, top_n: int = 5) -> list[tuple[str, int]]:
    """
    Return the top-N pages by in-degree (most linked-to pages).

    Time  : O(V + E)  — in-degree is computed from the adjacency list
    Space : O(V)
    """
    in_degrees = graph.all_in_degrees()
    ranked = sorted(in_degrees.items(), key=lambda x: x[1], reverse=True)
    return ranked[:top_n]


# ======================================================================
# 5. PAGERANK (simplified power iteration)
# ======================================================================

def pagerank(graph: DirectedGraph, damping: float = 0.85, iterations: int = 10) -> dict[str, float]:
    """
    Simplified PageRank via power iteration.

    Formula (per iteration)
    -----------------------
    PR(u) = (1 - d) / N  +  d * Σ_{v -> u}  PR(v) / out_degree(v)

    Where d = damping factor (typically 0.85), N = number of nodes.

    Dangling nodes (out-degree 0) redistribute their rank equally
    to all nodes to avoid rank sinks.

    Complexity
    ----------
    Time  : O(k * (V + E))  where k = number of iterations
    Space : O(V)
    """
    nodes = graph.nodes()
    N = len(nodes)
    if N == 0:
        return {}

    # Uniform initialisation
    rank = {n: 1.0 / N for n in nodes}

    dangling = graph.dangling_nodes()

    for _ in range(iterations):
        new_rank: dict[str, float] = {}

        # Dangling node contribution distributed uniformly
        dangling_sum = sum(rank[n] for n in dangling)
        dangling_contrib = damping * dangling_sum / N

        for node in nodes:
            # Teleportation
            base = (1.0 - damping) / N + dangling_contrib

            # Accumulate rank from in-neighbours
            link_sum = 0.0
            for pred in graph.predecessors(node):
                out_d = graph.out_degree(pred)
                if out_d > 0:
                    link_sum += rank[pred] / out_d

            new_rank[node] = base + damping * link_sum

        rank = new_rank

    return rank


# ======================================================================
# 6. DIJKSTRA'S ALGORITHM — single-source shortest path
# ======================================================================

def dijkstra(graph: DirectedGraph, source: str) -> tuple[dict[str, float], dict[str, str | None]]:
    """
    Dijkstra's single-source shortest-path algorithm.

    Uses a min-heap (priority queue) so we always relax the cheapest
    known frontier node first, guaranteeing optimal distances even when
    edge weights differ.

    Algorithm
    ---------
    1. Initialise dist[source] = 0, dist[all others] = ∞.
    2. Push (0, source) onto the min-heap.
    3. While heap is not empty:
       a. Pop (d, u) — the cheapest unprocessed node.
       b. Skip if d > dist[u]  (stale entry from a previous relaxation).
       c. For each neighbour v with edge weight w:
          if dist[u] + w < dist[v]:  relax — update dist[v] and prev[v],
                                      push (dist[v], v) onto the heap.
    4. Return dist (all shortest distances) and prev (predecessor map).

    Complexity
    ----------
    Time  : O((V + E) log V)  — each edge triggers at most one heap push
    Space : O(V)              — dist and prev arrays

    Parameters
    ----------
    graph  : DirectedGraph with edge weights set via add_edge(..., weight=w)
    source : starting node

    Returns
    -------
    dist : {node: shortest_distance}  (∞ means unreachable)
    prev : {node: predecessor_on_shortest_path}  (None means no predecessor)
    """
    nodes = graph.nodes()
    dist: dict[str, float] = {node: float("inf") for node in nodes}
    prev: dict[str, str | None] = {node: None for node in nodes}

    if source not in dist:
        return dist, prev

    dist[source] = 0.0
    heap: list[tuple[float, str]] = [(0.0, source)]

    while heap:
        d, u = heapq.heappop(heap)
        if d > dist[u]:          # stale heap entry — skip
            continue
        for v, w in graph.weighted_successors(u):
            new_dist = dist[u] + w
            if new_dist < dist[v]:
                dist[v] = new_dist
                prev[v] = u
                heapq.heappush(heap, (new_dist, v))

    return dist, prev


def reconstruct_path(
    prev: dict[str, str | None], source: str, target: str
) -> list[str] | None:
    """
    Walk the predecessor map backwards from target to source.

    Returns the path as a list [source, ..., target], or None if
    target is unreachable from source.
    """
    if target not in prev:
        return None
    if prev[target] is None and target != source:
        return None       # target was never relaxed

    path: list[str] = []
    node: str | None = target
    while node is not None:
        path.append(node)
        node = prev[node]
    path.reverse()

    return path if path[0] == source else None
