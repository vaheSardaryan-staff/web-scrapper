# Web Crawler & Link Graph Analyzer

A Python project that simulates a web crawler on a local "web" of text files,
builds a directed graph using an adjacency list, and runs graph analysis
algorithms (BFS, DFS, Kosaraju SCC, topological sort, PageRank) to extract
structural insights from the link graph.

## Requirements

- Python 3.10+
- **No third-party libraries** — only the standard library (tkinter is built-in)

## How to Run

```bash
python main.py
```

This launches a Tkinter GUI with 7 tabs. Select a root page and click
**[ RUN CRAWLER ]** to crawl the local web and populate all analysis tabs.

---

## Problem Breakdown & Modular Design

The project was decomposed into four independent modules, each responsible
for a single concern. This keeps the codebase maintainable and testable:

```
web_crawler/
├── main.py              ← Entry point — launches the GUI
├── pages/               ← 15 simulated web pages (.txt files)
│   ├── home.txt
│   ├── about.txt
│   └── ...
└── src/
    ├── graph.py          ← Module 1: Data structure (DirectedGraph)
    ├── crawler.py        ← Module 2: BFS crawling engine
    ├── algorithms.py     ← Module 3: Graph analysis algorithms
    └── gui.py            ← Module 4: Tkinter GUI (presentation)
```

### Module Responsibilities

| Module | Responsibility | Key Classes / Functions |
|---|---|---|
| `graph.py` | Directed graph ADT (adjacency list). Encapsulates all graph state and exposes query methods. No algorithm logic lives here. | `DirectedGraph` |
| `crawler.py` | Reads `.txt` page files, performs BFS traversal from a root, and populates a `DirectedGraph`. Handles missing files and dangling references. | `WebCrawler`, `parse_page()` |
| `algorithms.py` | Pure algorithm functions that receive a `DirectedGraph` and return results. Stateless — easy to test in isolation. | `kosaraju_scc()`, `topological_sort()`, `condense_graph()`, `find_hubs()`, `pagerank()`, `dfs_finish_order()` |
| `gui.py` | Presentation layer. Calls the crawler and algorithm functions, then renders results in 7 notebook tabs. | `App` |

This separation means any module can be modified or tested without affecting
the others. For example, swapping Kosaraju for Tarjan would only touch
`algorithms.py`.

---

## OOP Principles

### Encapsulation

`DirectedGraph` encapsulates the adjacency list (`_adj`), reverse adjacency
list (`_radj`), and node set (`_nodes`) as private attributes. External code
interacts through public methods (`add_edge`, `successors`, `in_degree`, etc.)
and never accesses the internal data structures directly.

`WebCrawler` encapsulates the crawl state (`graph`, `crawl_order`,
`page_metadata`) and exposes a single `crawl(root)` method as its public API.

### Polymorphism

The `DirectedGraph` class implements `__repr__` for a human-readable string
representation, allowing it to be printed or logged via Python's standard
`print()` / `repr()` protocol.

### Inheritance

`App` inherits from `tk.Tk`, extending the base Tkinter window class with
application-specific tabs, layout, and event handling.

---

## Core Algorithms

### 1. BFS Web Crawl (`crawler.py`)

The crawler discovers pages using **Breadth-First Search**:

1. Enqueue the root page; mark it visited.
2. While the queue is not empty:
   - Dequeue page `p`; record it in discovery order.
   - Parse `p`'s file; for each outgoing link `L`, add edge `p → L`.
   - If `L` has not been visited and its file exists, enqueue it.
3. Return the completed `DirectedGraph`.

### 2. DFS — Finish Order (`algorithms.py`)

An **iterative DFS** that returns nodes in post-order (finish order). Uses an
explicit stack of `(node, iterator)` pairs to avoid Python's recursion limit.
This is a helper used internally by Kosaraju's algorithm.

### 3. Kosaraju's Algorithm — SCC Detection (`algorithms.py`)

Finds all **Strongly Connected Components** in two passes:

- **Pass 1**: Run DFS on the original graph; collect nodes in finish order.
- **Pass 2**: Build the reversed graph. Process nodes in reverse finish order;
  each DFS tree in this pass is one SCC.

### 4. Graph Condensation + Topological Sort (`algorithms.py`)

- **Condensation**: Each SCC is collapsed into a single super-node. Edges
  between SCCs in the original graph become edges between super-nodes. The
  result is a DAG.
- **Kahn's Algorithm**: BFS-based topological sort on the condensation DAG.
  Repeatedly removes nodes with in-degree 0 and appends them to the result.

### 5. Hub Pages — In-Degree Ranking (`algorithms.py`)

Computes the in-degree of every node and returns the top-N pages sorted by
in-degree. Pages with the highest in-degree are the most linked-to ("hub")
pages.

### 6. PageRank — Power Iteration (Bonus) (`algorithms.py`)

Simplified PageRank using 10 iterations of the power method:

```
PR(u) = (1 - d) / N  +  d * Σ_{v → u}  PR(v) / out_degree(v)
```

Where `d = 0.85` (damping factor) and `N` = number of nodes. Dangling nodes
(out-degree 0) redistribute their rank equally to all nodes to prevent rank
sinks.

---

## Edge Cases Handled

| Edge Case | How It Is Handled |
|---|---|
| **Dangling pages** (no outgoing links) | Detected via `out_degree == 0`. In PageRank, their rank is redistributed uniformly to all nodes. |
| **Self-loops** (page links to itself) | Stored as a normal edge. Detected and reported via `DirectedGraph.self_loops()`. |
| **Cycles** | Kosaraju's algorithm groups cyclic pages into SCCs. The condensation DAG removes cycles for topological sort. |
| **Missing page files** | BFS adds the node to the graph and marks it as "not found" in metadata, but does not attempt to crawl it further. |
| **Duplicate edges** | `add_edge` checks for duplicates before inserting (`if dst not in self._adj[src]`). |
| **Empty graph** | `pagerank()` returns `{}` for an empty graph. All algorithms handle `V = 0` gracefully. |

---

## Asymptotic Complexity Analysis

All complexities are expressed in terms of **V** (number of pages/vertices)
and **E** (number of links/directed edges).

### Time Complexity

| Algorithm | Time | Justification |
|---|---|---|
| BFS Crawl | O(V + E) | Each page is dequeued once (V). Each link is traversed once to add an edge (E). |
| DFS (finish order) | O(V + E) | Each node is pushed/popped from the stack once. Each edge is iterated once via the successor iterator. |
| Kosaraju SCC | O(V + E) | Two full DFS passes over all nodes and edges: Pass 1 on the original graph, Pass 2 on the reversed graph. Constructing the reverse graph is also O(V + E). |
| Graph Condensation | O(V + E) | Mapping each node to its SCC index: O(V). Scanning every edge to build the DAG: O(E). |
| Kahn's Topo Sort | O(V + E) | Each super-node is enqueued/dequeued once. Each DAG edge is processed once when decrementing in-degrees. |
| In-Degree / Hubs | O(V + E) | In-degrees are computed by counting predecessors across all edges. Sorting V nodes adds O(V log V), dominated by O(V + E) for typical graphs. |
| PageRank (k iters) | O(k * (V + E)) | Each iteration visits every node and traverses every edge to accumulate rank from predecessors. With k = 10, this is 10 * O(V + E). |

### Space Complexity

| Algorithm | Space | Justification |
|---|---|---|
| BFS Crawl | O(V) | The BFS queue holds at most V nodes. The visited set is O(V). |
| DFS (finish order) | O(V) | The explicit stack depth is bounded by V (longest simple path). |
| Kosaraju SCC | O(V + E) | Requires storing the reversed graph (V nodes + E edges) plus the finish-order list (V) and visited set (V). |
| Graph Condensation | O(V + E) | The condensation DAG has at most V super-nodes and E edges. The node-to-SCC mapping is O(V). |
| Kahn's Topo Sort | O(V) | In-degree array and queue are both O(V). |
| In-Degree / Hubs | O(V) | Stores one integer per node. |
| PageRank (k iters) | O(V) | Two rank vectors of size V (current and next iteration). |
| DirectedGraph | O(V + E) | Adjacency list `_adj` and reverse list `_radj` each store all edges. Node set `_nodes` stores V entries. |

### Overall Pipeline

The full analysis pipeline (crawl → SCC → condensation → topo sort → hubs →
PageRank) runs in **O(V + E)** time, with PageRank adding a constant factor
of k = 10. For the 15-page local web, V = 15 and E ≈ 20, so all operations
are effectively instantaneous.

---

## Empirical Performance Testing

To validate the theoretical complexity analysis, we benchmarked every algorithm
on randomly generated directed graphs of increasing size (50 to 5,000 nodes,
with ~3 edges per node). Each measurement is averaged over 5 runs.

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

On the log-log plot, all algorithms follow the dashed O(V) reference line,
confirming linear O(V + E) growth. PageRank runs ~10× slower than a single
BFS pass, consistent with its k = 10 iteration factor.

### Individual Algorithm Scaling

![Per-algorithm scaling](benchmarks/per_algorithm_scaling.png)

### Interpretation

- All algorithms grow **linearly** with graph size, matching the theoretical
  O(V + E) analysis.
- **PageRank** is the most expensive per call due to its 10 iterations, but
  still scales linearly.
- **Kosaraju SCC** costs roughly 2× DFS because it performs two full traversals
  plus a graph reversal.
- The log-log plot's parallel lines confirm that constant-factor differences
  exist but the **asymptotic growth rate is the same** across all algorithms.

---

## The Simulated Web (15 pages)

Each page is a `.txt` file in the `pages/` directory with the format:

```
TITLE: Page Title
DESCRIPTION: Short description of the page.
LINKS:
linked_page_1
linked_page_2
```

### Link Graph

```
home ──► about ──► team ──► careers ──► contact
  │                                        │
  ├──► blog ──► blog_post1 ◄──────────────┤
  │        └──► blog_post2                 │
  │        └──► blog_post3                 │
  │                                        │
  ├──► products ──► product_alpha ◄───────► product_beta
  │            └──► pricing ──► faq ──► docs
  │
  └──► contact
```

The graph contains:
- **Cycles**: `product_alpha ↔ product_beta` form a mutual link cycle (SCC).
- **Dangling pages**: `docs`, `blog_post2`, `blog_post3`, `careers` have no outgoing links.
- **High in-degree hub**: `contact` is linked from multiple pages.

---

## GUI Tabs

1. **CRAWL** — Choose root page, run BFS, see discovery order and edge cases
2. **GRAPH** — Full adjacency list with in/out degrees for every node
3. **SCCs** — Kosaraju's result; which pages form cycles
4. **TOPO SORT** — Condensation DAG displayed in topological order
5. **HUBS** — Pages ranked by in-degree with visual bar chart
6. **PAGERANK** — PageRank scores after 10 iterations with visual bars
7. **COMPLEXITY** — Big-O analysis table for every algorithm
