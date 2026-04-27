# Web Crawler & Link Graph Analyzer

A Python project that simulates a web crawler on a local "web" of text files,
builds a weighted directed graph using an adjacency list, and runs a full suite
of graph analysis algorithms to extract structural insights from the link graph.

The project ships with a dark-themed Tkinter GUI featuring 11 interactive tabs —
no third-party libraries required.

---

## Table of Contents

1. [Requirements](#requirements)
2. [How to Run](#how-to-run)
3. [Project Structure](#project-structure)
4. [Module Reference](#module-reference)
   - [graph.py — DirectedGraph ADT](#graphpy--directedgraph-adt)
   - [crawler.py — Web Crawler](#crawlerpy--web-crawler)
   - [algorithms.py — Graph Algorithms](#algorithmspy--graph-algorithms)
   - [gui.py — Tkinter GUI](#guipy--tkinter-gui)
5. [Crawl Modes](#crawl-modes)
6. [Core Algorithms](#core-algorithms)
7. [GUI Tabs](#gui-tabs)
8. [OOP Principles](#oop-principles)
9. [Edge Cases Handled](#edge-cases-handled)
10. [Asymptotic Complexity Analysis](#asymptotic-complexity-analysis)
11. [Empirical Performance Benchmarks](#empirical-performance-benchmarks)
12. [The Simulated Web](#the-simulated-web)

---

## Requirements

- Python 3.10+
- **No third-party runtime libraries** — only the Python standard library (`tkinter` is built-in)
- `matplotlib` is required only to regenerate benchmark plots:
  ```bash
  pip install matplotlib
  python benchmark.py
  ```

---

## How to Run

```bash
python main.py
```

This launches the Tkinter GUI. Select a root page, choose a crawl mode and
optional depth limit, then click **[ RUN CRAWLER ]**. All 11 analysis tabs
populate automatically.

---

## Project Structure

```
web_crawler/
├── main.py                  ← Entry point — creates App and starts the event loop
├── benchmark.py             ← Standalone benchmark script (matplotlib required)
├── benchmarks/              ← Saved benchmark plots
│   ├── execution_time_linear.png
│   ├── execution_time_loglog.png
│   └── per_algorithm_scaling.png
├── pages/                   ← 15 simulated web pages (.txt files)
│   ├── home.txt
│   ├── about.txt
│   ├── blog.txt
│   ├── blog_post1.txt
│   ├── blog_post2.txt
│   ├── blog_post3.txt
│   ├── team.txt
│   ├── careers.txt
│   ├── contact.txt
│   ├── products.txt
│   ├── product_alpha.txt
│   ├── product_beta.txt
│   ├── pricing.txt
│   ├── faq.txt
│   └── docs.txt
├── src/
│   ├── __init__.py
│   ├── graph.py             ← Module 1: DirectedGraph ADT (adjacency list)
│   ├── crawler.py           ← Module 2: BFS / Priority / depth-limited crawler
│   ├── algorithms.py        ← Module 3: All graph analysis algorithms
│   └── gui.py               ← Module 4: Tkinter GUI (11 tabs)
└── tests/
    ├── __init__.py
    ├── test_graph.py
    ├── test_crawler.py
    └── test_algorithms.py
```

The project is decomposed into four independent modules, each with a single
responsibility. Any module can be modified, replaced, or tested in isolation
without touching the others.

| Module | Responsibility | Key Exports |
|---|---|---|
| `graph.py` | Directed graph ADT. Encapsulates all graph state behind a clean API. No algorithm logic lives here. | `DirectedGraph` |
| `crawler.py` | Reads `.txt` page files, performs BFS or priority crawl from a root, and populates a `DirectedGraph`. Handles missing files and dangling references. | `WebCrawler`, `parse_page()` |
| `algorithms.py` | Pure, stateless algorithm functions. Each receives a `DirectedGraph` and returns results. Easy to unit-test in isolation. | `kosaraju_scc`, `topological_sort`, `condense_graph`, `find_hubs`, `pagerank`, `dijkstra`, `reconstruct_path`, `hits`, `floyd_warshall`, `graph_diameter`, `reconstruct_fw_path` |
| `gui.py` | Presentation layer. Drives the crawler and algorithms, renders results across 11 notebook tabs. | `App` |

---

## Module Reference

### graph.py — DirectedGraph ADT

`DirectedGraph` is an adjacency-list directed graph with weighted edges.

**Internal storage**

| Attribute | Type | Purpose |
|---|---|---|
| `_adj` | `defaultdict(list)` | Forward adjacency list: `node → [successors]` |
| `_radj` | `defaultdict(list)` | Reverse adjacency list: `node → [predecessors]` |
| `_nodes` | `set` | Full node set (includes isolates with no edges) |
| `_weights` | `dict[(src, dst), float]` | Edge weight map (default weight `1.0`) |

The reverse adjacency list is maintained in sync with `_adj` at every
`add_edge` call, so Kosaraju's algorithm can access `predecessors(node)` in
O(1) without constructing a separate reversed graph at query time.
`reverse()` still returns a proper reversed copy for algorithms that need it.

**Public API**

```
add_node(node)                        → registers a node with no edges
add_edge(src, dst, weight=1.0)        → adds a directed weighted edge; ignores duplicates
nodes()                               → list of all node names
successors(node)                      → list of out-neighbours
predecessors(node)                    → list of in-neighbours
in_degree(node) / out_degree(node)    → degree queries
all_in_degrees()                      → {node: in_degree} for every node
num_nodes() / num_edges()             → graph size
get_weight(src, dst)                  → edge weight (1.0 if not set)
weighted_successors(node)             → [(successor, weight), …]
is_dangling(node) / dangling_nodes()  → nodes with out-degree 0
self_loops()                          → nodes where src == dst
reverse()                             → new DirectedGraph with all edges flipped
__repr__()                            → human-readable adjacency list
```

**Space complexity:** O(V + E) — the forward and reverse adjacency lists each
store all edges; the weight map is O(E).

---

### crawler.py — Web Crawler

`WebCrawler` reads `.txt` page files from a directory and builds a
`DirectedGraph` via one of two crawl strategies.

**Page file format**

```
TITLE: Page Title
DESCRIPTION: Short description of the page.
LINKS:
linked_page_1
linked_page_2  2.5
```

Link lines are `page_name [weight]`. If a weight is omitted it defaults to
`1.0`. The parser is implemented in the free function `parse_page(filepath)`.

**Attributes populated after a crawl**

| Attribute | Type | Contents |
|---|---|---|
| `graph` | `DirectedGraph` | The completed link graph |
| `crawl_order` | `list[str]` | Pages in discovery order |
| `page_metadata` | `dict[str, dict]` | `{page: {"title": …, "description": …}}` |
| `crawl_depth` | `dict[str, int]` | Hop distance from root (both modes) |
| `crawl_costs` | `dict[str, float]` | Cumulative edge-weight cost (priority crawl only) |

See [Crawl Modes](#crawl-modes) for algorithm details.

---

### algorithms.py — Graph Algorithms

Every function in this module is **stateless**: it receives a `DirectedGraph`
(and optional parameters) and returns a result. No side effects, no global
state. This makes every algorithm trivially unit-testable.

See [Core Algorithms](#core-algorithms) for full descriptions.

**Exported names**

| Function | Returns |
|---|---|
| `dfs_finish_order(graph, start, visited)` | `list[str]` — nodes in DFS finish order |
| `kosaraju_scc(graph)` | `list[list[str]]` — list of SCCs, largest first |
| `condense_graph(graph, sccs)` | `(node_to_scc_map, condensed_dag)` |
| `topological_sort(dag)` | `list[str]` — Kahn's topological order |
| `find_hubs(graph, top_n)` | `list[(page, in_degree)]` |
| `pagerank(graph, damping, iterations)` | `dict[str, float]` |
| `dijkstra(graph, source)` | `(dist_map, prev_map)` |
| `reconstruct_path(prev, source, target)` | `list[str]` or `None` |
| `hits(graph, iterations)` | `(hub_scores, auth_scores)` |
| `floyd_warshall(graph)` | `(dist_matrix, next_hop_matrix)` |
| `graph_diameter(dist)` | `(diameter, src, dst)` |
| `reconstruct_fw_path(next_hop, src, dst)` | `list[str]` or `None` |

---

### gui.py — Tkinter GUI

`App` inherits from `tk.Tk` and builds a single-window application with a
dark monochrome colour scheme and 11 notebook tabs. The GUI is the only layer
that calls the crawler and algorithm functions; all other modules are
presentation-agnostic.

After a crawl completes, `_refresh_all_tabs()` pushes updated data to every
tab simultaneously.

---

## Crawl Modes

### BFS (Breadth-First Search)

The default mode. Explores pages level-by-level from the root.

**Algorithm**

1. Enqueue `(root, depth=0)`; mark it visited.
2. While the queue is not empty:
   - Dequeue `(page, depth)`; record it in discovery order.
   - Parse the page file; store metadata.
   - For each link `L` with weight `w`: call `add_edge(page, L, w)`.
   - If `L` has not been visited, and `depth + 1 ≤ max_depth` (or
     `max_depth` is `None`), and the file exists: enqueue `(L, depth+1)`.
3. Return the completed `DirectedGraph`.

**Complexity:** O(V + E) time, O(V) space.

### Depth-Limited BFS

Same as BFS but stops expanding beyond a configurable `max_depth`. Set
`max_depth = 0` in the GUI spinner for unlimited crawl. Pages beyond the
depth limit are still added as nodes (so their links appear in the graph),
but they are not themselves crawled.

### Priority Crawl (Best-First by Cost)

A min-heap best-first search: always visits the cheapest-to-reach unvisited
page next, where cost is the cumulative sum of edge weights along the path
from root.

**Algorithm**

1. Push `(cost=0.0, depth=0, root)` onto the min-heap.
2. While the heap is not empty:
   - Pop `(cost, depth, page)` — the globally cheapest unprocessed page.
   - If `page` was already processed at equal or lower cost: skip (stale entry).
   - Record `page` in crawl order; store its depth and cumulative cost.
   - Parse the page file; for each link `L` with weight `w`:
     - `new_cost = cost + w`
     - If `new_cost < best[L]`: update `best[L]` and push `(new_cost, depth+1, L)`.
3. Return the completed `DirectedGraph`.

Unlike BFS (which minimises hop count), the priority crawl minimises
cumulative traversal cost. A page reachable via a long cheap path can
be discovered before a directly-linked but expensive page.

**Complexity:** O((V + E) log V) time, O(V) space — same as Dijkstra.

---

## Core Algorithms

### 1. Iterative DFS — Finish Order (`dfs_finish_order`)

An iterative post-order DFS that returns nodes in finish order (a node is
appended only after all its descendants finish). Uses an explicit stack of
`(node, iterator_over_successors)` pairs to avoid Python's default recursion
limit on large graphs. Used internally by Kosaraju's algorithm.

**Complexity:** O(V + E) time, O(V) space.

---

### 2. Kosaraju's Algorithm — Strongly Connected Components (`kosaraju_scc`)

Finds all **Strongly Connected Components** — maximal subsets of pages where
every page is reachable from every other page via directed links.

**Two-pass algorithm**

- **Pass 1:** Run DFS on the original graph; collect all nodes in finish order.
- **Pass 2:** Build the reversed graph. Process nodes in *reverse* finish order;
  each DFS tree in this pass is exactly one SCC.

**Complexity:** O(V + E) time (two full DFS passes), O(V + E) space
(reversed graph + finish-order list).

---

### 3. Graph Condensation (`condense_graph`)

Collapses each SCC into a single super-node and builds a condensation DAG.
Edges between SCCs in the original graph become edges between super-nodes;
intra-SCC edges are dropped. The result is guaranteed to be a DAG.

**Complexity:** O(V + E) time, O(V + E) space.

---

### 4. Kahn's Topological Sort (`topological_sort`)

BFS-based topological sort on the condensation DAG.

**Algorithm**

1. Compute in-degree for every node.
2. Enqueue all nodes with in-degree 0.
3. While queue is not empty:
   - Dequeue node `u`; append to result.
   - For each successor `v`: decrement `in_degree(v)`.
     If `in_degree(v) == 0`: enqueue `v`.

**Complexity:** O(V + E) time, O(V) space.

---

### 5. Hub Pages — In-Degree Ranking (`find_hubs`)

Computes the in-degree of every node and returns the top-N pages sorted by
in-degree descending. Pages with the highest in-degree are the most
linked-to ("hub") pages in the web.

**Complexity:** O(V + E) time, O(V) space.

---

### 6. PageRank — Power Iteration (`pagerank`)

Simplified PageRank using iterative power-method updates:

```
PR(u) = (1 - d) / N  +  d × Σ_{v → u}  PR(v) / out_degree(v)
```

Where `d = 0.85` (damping factor) and `N` = number of nodes. Dangling nodes
(out-degree 0) redistribute their rank equally to all nodes to prevent rank
sinks. Runs for `k = 10` iterations by default.

**Complexity:** O(k × (V + E)) time, O(V) space.

---

### 7. Dijkstra's Algorithm — Single-Source Shortest Path (`dijkstra`)

Finds the minimum-cost path from a source node to all other nodes using a
min-heap priority queue.

**Algorithm**

1. Initialise `dist[source] = 0`, `dist[all others] = ∞`.
2. Push `(0, source)` onto the min-heap.
3. While heap is not empty:
   - Pop `(d, u)` — cheapest known unprocessed node.
   - Skip if `d > dist[u]` (stale heap entry).
   - For each successor `v` with edge weight `w`:
     if `dist[u] + w < dist[v]`: relax — update `dist[v]` and `prev[v]`,
     push `(dist[v], v)`.
4. Return `dist` (all shortest distances) and `prev` (predecessor map).

Call `reconstruct_path(prev, source, target)` to walk the predecessor map
and recover the actual path as a list.

**Complexity:** O((V + E) log V) time, O(V) space.

---

### 8. HITS — Hyperlink-Induced Topic Search (`hits`)

Computes two complementary scores via alternating power iteration
(Kleinberg 1999):

```
authority(u) ← Σ_{v → u} hub(v)      # pointed to by good hubs
hub(u)       ← Σ_{u → v} auth(v)     # points to good authorities
```

Both vectors are L2-normalised after every iteration so scores remain
comparable across graphs of different sizes. Runs for `k = 20` iterations.

**Contrast with PageRank:** PageRank assigns one general-importance score per
page. HITS separates two distinct roles — a page can be a strong hub but a
weak authority, or vice versa.

**Complexity:** O(k × (V + E)) time, O(V) space.

---

### 9. Floyd-Warshall — All-Pairs Shortest Path (`floyd_warshall`)

Computes optimal distances between **all pairs** of nodes in a single DP pass:

```
for k in nodes:
    for i in nodes:
        for j in nodes:
            if dist[i][k] + dist[k][j] < dist[i][j]:
                dist[i][j]     ← dist[i][k] + dist[k][j]
                next_hop[i][j] ← next_hop[i][k]
```

Returns both the full distance matrix and a `next_hop` matrix for path
reconstruction. `graph_diameter` extracts the longest finite shortest path
from the distance matrix. `reconstruct_fw_path` walks the next-hop table to
recover any specific path.

**When to use Floyd-Warshall vs Dijkstra×V:**
Floyd-Warshall runs in O(V³) regardless of edge density. Running Dijkstra
from every source is O(V × (V + E) log V), which is faster on sparse graphs
(E ≪ V²) but slower on dense graphs (E ≈ V²). For the 15-page local web both
are instantaneous; for large sparse crawls, Dijkstra×V is preferred.

**Complexity:** O(V³) time, O(V²) space.

---

## GUI Tabs

The application window contains 11 tabs. All tabs except CRAWL and COMPLEXITY
display a placeholder until the crawler has been run at least once.

| # | Tab | Description |
|---|---|---|
| 1 | **CRAWL** | Select root page, crawl mode (BFS / Priority), and max depth. Displays discovery order with hop depths or cumulative costs. Reports edge-case detections (dangling pages, self-links). |
| 2 | **GRAPH** | Full adjacency list with in-degree, out-degree, and successor list for every node. Flags dangling and self-loop nodes inline. |
| 3 | **VISUALIZE** | Interactive force-directed spring layout (Fruchterman-Reingold algorithm). Nodes are colour-coded: teal = regular, amber = dangling, green = member of a cycle (SCC). Click **REDRAW** to re-randomise the layout. Edge weights are labelled at the midpoint of each arrow. Bidirectional edges are offset so arrows don't overlap. |
| 4 | **SCCs** | Kosaraju's algorithm result. Lists multi-node SCCs (pages forming mutual-link cycles) separately from single-node SCCs. |
| 5 | **TOPO SORT** | Condensation DAG and Kahn's topological order. Each entry maps a super-node label to the member pages of its SCC. |
| 6 | **HUBS** | All pages ranked by in-degree with an ASCII bar chart. Top-3 highlighted in teal, top-8 in blue. |
| 7 | **PAGERANK** | PageRank scores after 10 iterations with ASCII bar chart. Shows the formula, damping factor, and iteration count. |
| 8 | **HITS** | HITS authority and hub scores displayed in ranked tables with bar charts. Includes a side-by-side explanation comparing HITS vs PageRank and the per-iteration update formulas. |
| 9 | **SHORTEST PATH** | Dijkstra's algorithm with interactive source/destination dropdowns. Displays the optimal path, total cost, hop count, step-by-step cost breakdown, and full distance table for all reachable pages from the source. |
| 10 | **ALL PAIRS** | Floyd-Warshall result. Shows the graph diameter and farthest node pair, the top-10 longest shortest paths with full route reconstruction, a reachability summary, and the complete V×V distance matrix. |
| 11 | **COMPLEXITY** | Big-O reference table for every algorithm in the project (time and space), notation key, and overall pipeline summary. |

---

## OOP Principles

### Encapsulation

`DirectedGraph` keeps `_adj`, `_radj`, `_nodes`, and `_weights` as private
attributes. External code never accesses the raw data structures — it uses the
public API (`add_edge`, `successors`, `in_degree`, `get_weight`, etc.). This
means the internal representation (e.g. switching from a list to a set per
node) can be changed without affecting any other module.

`WebCrawler` encapsulates crawl state (`graph`, `crawl_order`,
`page_metadata`, `crawl_depth`, `crawl_costs`) and exposes two public methods
(`crawl`, `priority_crawl`) as its API. The GUI interacts only with these
methods; it never touches the crawler's internal state directly.

### Polymorphism

`DirectedGraph` implements `__repr__` for a human-readable string
representation, allowing it to be printed or logged via Python's standard
`print()` / `repr()` protocol without the caller knowing anything about the
internal structure.

### Inheritance

`App` inherits from `tk.Tk`, extending the base Tkinter window class with
the application's tabs, layout, event handling, and data refresh logic.

---

## Edge Cases Handled

| Edge Case | How It Is Handled |
|---|---|
| **Dangling pages** (no outgoing links) | Detected via `out_degree == 0`. In PageRank, their rank is redistributed uniformly to all nodes to prevent rank sinks. Flagged in the CRAWL and GRAPH tabs and colour-coded amber in VISUALIZE. |
| **Self-loops** (page links to itself) | Stored as a normal edge. Detected and reported via `DirectedGraph.self_loops()`. Displayed in the CRAWL tab and flagged in GRAPH. |
| **Cycles** | Kosaraju's algorithm groups cyclic pages into multi-node SCCs. The condensation DAG removes cycles for topological sort. Cycle members are colour-coded green in VISUALIZE. |
| **Missing page files** | BFS / Priority Crawl adds the node to the graph and marks it as "not found" in metadata, but does not attempt to crawl it further. |
| **Duplicate edges** | `add_edge` checks `if dst not in self._adj[src]` before inserting. Duplicate calls are silently ignored. |
| **Stale heap entries** (priority crawl) | Lazy deletion: if a popped entry has `cost > best[page]`, it is skipped. No explicit removal from the heap is needed. |
| **Depth limit** | Pages beyond `max_depth` are registered as nodes (so their links are visible in GRAPH) but are not crawled. Their metadata is set to "Depth limit reached." |
| **Unreachable nodes** (Dijkstra / Floyd-Warshall) | `dist[node]` remains `float("inf")`. `reconstruct_path` and `reconstruct_fw_path` return `None` for unreachable targets. The UI displays "unreachable" in the distance tables. |
| **Empty graph** | `pagerank()` and `hits()` return `{}` immediately. `floyd_warshall()` returns empty dicts. All algorithms handle `V = 0` gracefully without special-casing in the GUI. |

---

## Asymptotic Complexity Analysis

Complexities are expressed in terms of **V** (pages / vertices) and
**E** (links / directed edges). `k` denotes the number of iterations for
iterative algorithms.

### Time Complexity

| Algorithm | Time | Justification |
|---|---|---|
| BFS Crawl | O(V + E) | Each page is dequeued once; each link is traversed once to add an edge. |
| Depth-Limited BFS | O(V + E) | Same as BFS; depth check is O(1) per node. |
| Priority Crawl | O((V + E) log V) | Each page is pushed and popped from the min-heap at most once per relaxation. |
| DFS Finish Order | O(V + E) | Each node is pushed/popped from the explicit stack once. Each edge is iterated once via the successor iterator. |
| Kosaraju SCC | O(V + E) | Two full DFS passes over all nodes and edges. Constructing the reverse graph is also O(V + E). |
| Graph Condensation | O(V + E) | Mapping each node to its SCC index: O(V). Scanning every edge to build the DAG: O(E). |
| Kahn's Topo Sort | O(V + E) | Each super-node is enqueued/dequeued once. Each DAG edge is processed once when decrementing in-degrees. |
| In-Degree / Hubs | O(V + E) | In-degrees are computed by scanning all predecessors. Sorting V nodes: O(V log V), dominated by O(V + E) for typical graphs. |
| PageRank (k iters) | O(k × (V + E)) | Each iteration visits every node and traverses every edge to accumulate rank from predecessors. |
| Dijkstra | O((V + E) log V) | Each edge triggers at most one heap push O(log V); each node is popped once. |
| HITS (k iters) | O(k × (V + E)) | Each iteration scans all edges twice (authority update + hub update). |
| Floyd-Warshall | O(V³) | Three nested loops over all V vertices (intermediate, source, destination). |
| Spring Layout (viz) | O(iter × (V² + E)) | Each of 90 iterations computes V² repulsive forces and E attractive forces. Practical for V ≤ ~200. |

### Space Complexity

| Algorithm | Space | Justification |
|---|---|---|
| BFS / Priority Crawl | O(V) | Queue or heap holds at most V nodes; visited set is O(V). |
| DFS Finish Order | O(V) | Explicit stack depth is bounded by V (longest simple path). |
| Kosaraju SCC | O(V + E) | Reversed graph (V nodes, E edges) + finish-order list (V) + visited set (V). |
| Graph Condensation | O(V + E) | Condensation DAG has at most V super-nodes and E edges; node-to-SCC map is O(V). |
| Kahn's Topo Sort | O(V) | In-degree map and queue are both O(V). |
| In-Degree / Hubs | O(V) | One integer per node. |
| PageRank | O(V) | Two rank vectors of size V (current and next iteration). |
| Dijkstra | O(V) | `dist` and `prev` arrays are O(V); heap holds at most O(V) entries. |
| HITS | O(V) | Two score vectors (hub, auth) of size V each. |
| Floyd-Warshall | O(V²) | Full V×V distance matrix and next-hop matrix. |
| DirectedGraph | O(V + E) | `_adj`, `_radj`, and `_weights` together store all edges; `_nodes` is O(V). |

### Overall Pipeline

The full analysis pipeline (crawl → SCC → condensation → topo sort → hubs →
PageRank → HITS → Dijkstra → Floyd-Warshall) is dominated by Floyd-Warshall
at **O(V³)**. For the 15-page local web (V = 15, E ≈ 20), every step is
effectively instantaneous.

---

## Empirical Performance Benchmarks

To validate the theoretical complexity analysis, every algorithm was
benchmarked on randomly generated directed graphs of increasing size
(50 to 5,000 nodes, ~3 edges per node). Each measurement is the average of
5 runs.

### How to reproduce

```bash
pip install matplotlib
python benchmark.py
```

Plots are saved to `benchmarks/`.

### Results

| V     | E      | BFS     | DFS     | Kosaraju | Condense + Topo | PageRank (10 iter) |
|------:|-------:|--------:|--------:|---------:|----------------:|-------------------:|
| 50    | 148    | 0.02 ms | 0.04 ms | 0.17 ms  | 0.23 ms         | 0.37 ms            |
| 100   | 296    | 0.04 ms | 0.09 ms | 0.39 ms  | 0.47 ms         | 0.87 ms            |
| 500   | 1,496  | 0.003ms | 0.42 ms | 2.17 ms  | 2.27 ms         | 4.30 ms            |
| 1,000 | 2,992  | 0.37 ms | 0.82 ms | 3.98 ms  | 5.07 ms         | 9.73 ms            |
| 2,000 | 5,996  | 0.86 ms | 1.84 ms | 9.06 ms  | 12.20 ms        | 20.05 ms           |
| 5,000 | 14,998 | 2.46 ms | 5.46 ms | 28.61 ms | 30.20 ms        | 53.51 ms           |

### Execution Time vs Graph Size (linear scale)

![Linear scale benchmark](benchmarks/execution_time_linear.png)

### Log-Log Plot — Growth Rate Verification

![Log-log benchmark](benchmarks/execution_time_loglog.png)

On the log-log plot, all O(V + E) algorithms follow the dashed O(V) reference
line, confirming linear growth. PageRank runs ~10× slower than a single BFS
pass, consistent with its k = 10 iteration factor.

### Individual Algorithm Scaling

![Per-algorithm scaling](benchmarks/per_algorithm_scaling.png)

### Interpretation

- All O(V + E) algorithms grow **linearly** with graph size, matching the
  theoretical analysis.
- **PageRank** is the most expensive per call among the linear algorithms due
  to its 10 iterations, but still scales linearly.
- **Kosaraju SCC** costs roughly 2× DFS because it performs two full
  traversals plus a graph reversal.
- **Floyd-Warshall** is not included in the benchmark table above because its
  O(V³) growth would dwarf the other algorithms at V = 5,000.
- The log-log plot's parallel lines confirm that constant-factor differences
  exist but the **asymptotic growth rate is the same** across all O(V + E)
  algorithms.

---

## The Simulated Web

Each page is a `.txt` file in the `pages/` directory:

```
TITLE: Page Title
DESCRIPTION: Short description of the page.
LINKS:
linked_page_1
linked_page_2  2.5
```

Link lines can optionally carry a traversal cost (weight). Omitting the weight
defaults to `1.0`. This allows Dijkstra and the priority crawler to produce
paths that differ from simple hop-count BFS.

### Link Graph

```
home ──► about ──► team ──► careers ──► contact
  │                                        │
  ├──► blog ──► blog_post1 ◄──────────────┤
  │        └──► blog_post2                 │
  │        └──► blog_post3                 │
  │                                        │
  ├──► products ──► product_alpha ◄──────► product_beta
  │            └──► pricing ──► faq ──► docs
  │
  └──► contact
```

Interesting structural properties in this graph:

- **Cycle / SCC**: `product_alpha ↔ product_beta` form a mutual-link cycle —
  Kosaraju groups them into a 2-node SCC.
- **Dangling pages**: `docs`, `blog_post2`, `blog_post3`, and `careers` have
  no outgoing links. PageRank distributes their rank uniformly to prevent rank
  sinks.
- **High in-degree hub**: `contact` is linked from `home`, `careers`, and
  `blog_post1`, making it the top-ranked hub by in-degree and a strong
  authority under HITS.
- **Weighted edges**: link costs vary across pages, so Dijkstra and the
  priority crawler can discover a different traversal order than plain BFS.
