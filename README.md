# Web Crawler & Link Graph Analyzer

A Python project that simulates a web crawler on a local "web" of text files,
builds a directed graph, and runs graph analysis algorithms.

## Requirements

- Python 3.10+
- **No third-party libraries** — only the standard library (tkinter is built-in)

## Project Structure

```
web_crawler/
├── main.py           ← Launch the GUI
├── cli_demo.py       ← Headless CLI demo (no display needed)
├── pages/            ← 15 simulated web pages (.txt files)
│   ├── home.txt
│   ├── about.txt
│   └── ...
└── src/
    ├── graph.py      ← DirectedGraph (adjacency list)
    ├── crawler.py    ← BFS web crawler
    ├── algorithms.py ← Kosaraju SCC, Topo Sort, PageRank, Hubs
    └── gui.py        ← Tkinter GUI (7 tabs)
```

## How to Run

### GUI (recommended)
```bash
python main.py
```

### CLI demo (no display required)
```bash
python cli_demo.py
```

## Features

| Feature | Algorithm | Complexity |
|---|---|---|
| Web crawl | BFS | O(V+E) |
| Strongly Connected Components | Kosaraju's 2-Pass DFS | O(V+E) |
| Hub pages | In-degree ranking | O(V+E) |
| Topological sort | Kahn's BFS | O(V+E) |
| PageRank | Power iteration (10 iters) | O(k·(V+E)) |
| Edge cases | Dangling nodes, self-loops | O(V+E) |

## GUI Tabs

1. **CRAWL** — Choose root page, run BFS, see discovery order
2. **GRAPH** — Adjacency list with in/out degrees for every node
3. **SCCs** — Kosaraju's result; which pages form cycles
4. **TOPO SORT** — Condensation DAG in topological order
5. **HUBS** — Bar chart of most-linked pages
6. **PAGERANK** — PageRank scores with visual bars
7. **COMPLEXITY** — Big-O analysis table for every algorithm

## The Simulated Web (15 pages)

```
home ──► about ──► team ──► careers ──► contact
  │                                        │
  ├──► blog ──► blog_post1 ◄──────────────┤
  │        └──► blog_post2                 │
  │        └──► blog_post3                 │
  │                                        │
  ├──► products ──► product_alpha ◄───────►product_beta
  │            └──► pricing ──► faq ──► docs
  │
  └──► contact
```
