"""
crawler.py
----------
Web crawler that reads local .txt page files and builds a DirectedGraph.

Each page file has the format:
    TITLE: <title>
    DESCRIPTION: <desc>
    LINKS:
    <link1>
    <link2>
    ...

Crawling strategy: BFS from a root node.

BFS Time Complexity  : O(V + E)
BFS Space Complexity : O(V)   — the queue holds at most V nodes
"""

import heapq
import os
from collections import deque
from src.graph import DirectedGraph


def parse_page(filepath: str) -> tuple[str, str, list[tuple[str, float]]]:
    """
    Parse a page text file.

    Link lines may be either:
        page_name           → weight defaults to 1.0
        page_name  2.5      → explicit weight

    Returns
    -------
    title       : str
    description : str
    links       : list[tuple[str, float]]  — (page_name, weight)
    """
    title, description, links = "Unknown", "", []
    in_links_section = False

    with open(filepath, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith("TITLE:"):
                title = line[len("TITLE:"):].strip()
            elif line.startswith("DESCRIPTION:"):
                description = line[len("DESCRIPTION:"):].strip()
            elif line == "LINKS:":
                in_links_section = True
            elif in_links_section:
                parts = line.split()
                name = parts[0]
                if len(parts) >= 2:
                    try:
                        weight = float(parts[1])
                    except ValueError:
                        print(f"Warning: invalid weight {parts[1]!r} for link "
                              f"'{name}' in {filepath!r} — defaulting to 1.0")
                        weight = 1.0
                else:
                    weight = 1.0
                links.append((name, weight))

    return title, description, links


class WebCrawler:
    """
    Crawls a local 'web' of .txt files and builds a DirectedGraph via BFS.

    Attributes
    ----------
    pages_dir      : directory that contains the page .txt files
    graph          : the resulting DirectedGraph
    crawl_order    : list of node names in BFS discovery order
    page_metadata  : {name: {"title": ..., "description": ...}}
    """

    def __init__(self, pages_dir: str):
        self.pages_dir = pages_dir
        self.graph = DirectedGraph()
        self.crawl_order: list[str] = []
        self.page_metadata: dict[str, dict] = {}
        self.crawl_depth: dict[str, int] = {}    # hop depth from root
        self.crawl_costs: dict[str, float] = {}  # cumulative cost (priority crawl only)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def crawl(self, root: str, max_depth: int | None = None) -> DirectedGraph:
        """
        BFS crawl starting from `root`.

        Parameters
        ----------
        root      : starting page name
        max_depth : maximum hop depth to explore (None = unlimited).
                    depth 0 = root only, depth 1 = root + direct links, etc.

        Algorithm
        ---------
        1. Enqueue (root, depth=0); mark it visited.
        2. While queue is not empty:
           a. Dequeue (page, depth); record discovery order.
           b. Read page's file; store metadata.
           c. For each link L: add edge, enqueue L at depth+1
              only if depth+1 <= max_depth (or max_depth is None).
        3. Return completed graph.

        Complexity: O(V + E)  where V = pages, E = links
        """
        self.graph = DirectedGraph()
        self.crawl_order = []
        self.page_metadata = {}
        self.crawl_depth = {}
        self.crawl_costs = {}

        visited: set[str] = set()
        queue: deque[tuple[str, int]] = deque()

        if not self._file_exists(root):
            raise FileNotFoundError(f"Root page '{root}' not found in {self.pages_dir}")

        queue.append((root, 0))
        visited.add(root)
        self.graph.add_node(root)
        self.crawl_depth[root] = 0

        while queue:
            page, depth = queue.popleft()
            self.crawl_order.append(page)

            filepath = self._filepath(page)
            if os.path.exists(filepath):
                title, desc, links = parse_page(filepath)
                self.page_metadata[page] = {"title": title, "description": desc}

                for link, weight in links:
                    self.graph.add_edge(page, link, weight=weight)

                    if link not in visited:
                        visited.add(link)
                        new_depth = depth + 1
                        self.crawl_depth[link] = new_depth
                        within_limit = (max_depth is None or new_depth <= max_depth)
                        if within_limit and self._file_exists(link):
                            queue.append((link, new_depth))
                        else:
                            self.graph.add_node(link)
                            self.page_metadata[link] = {
                                "title": f"{link} (not found)" if not self._file_exists(link)
                                         else link,
                                "description": "Page file does not exist."
                                               if not self._file_exists(link)
                                               else "Depth limit reached — not crawled.",
                            }
            else:
                self.page_metadata[page] = {
                    "title": f"{page} (not found)",
                    "description": "Page file does not exist.",
                }

        return self.graph

    def priority_crawl(self, root: str) -> DirectedGraph:
        """
        Min-heap priority crawl: always visits the cheapest-to-reach
        unvisited page next (best-first search by cumulative edge cost).

        Unlike BFS (which explores by hop count), this explores by cost,
        so a page reachable at low weight via a long path can be discovered
        before a directly-linked but expensive page.

        Data structure: min-heap of (cumulative_cost, hop_depth, page).

        Complexity: O((V + E) log V)  — same as Dijkstra
        """
        self.graph = DirectedGraph()
        self.crawl_order = []
        self.page_metadata = {}
        self.crawl_depth = {}
        self.crawl_costs = {}

        if not self._file_exists(root):
            raise FileNotFoundError(f"Root page '{root}' not found in {self.pages_dir}")

        self.graph.add_node(root)
        heap: list[tuple[float, int, str]] = [(0.0, 0, root)]
        best: dict[str, float] = {root: 0.0}

        while heap:
            cost, depth, page = heapq.heappop(heap)

            # Already processed this page at equal or lower cost — skip
            if page in self.crawl_depth:
                continue

            self.crawl_order.append(page)
            self.crawl_depth[page] = depth
            self.crawl_costs[page] = cost

            filepath = self._filepath(page)
            if os.path.exists(filepath):
                title, desc, links = parse_page(filepath)
                self.page_metadata[page] = {"title": title, "description": desc}

                for link, weight in links:
                    self.graph.add_edge(page, link, weight=weight)
                    new_cost = cost + weight

                    if link not in self.crawl_depth and new_cost < best.get(link, float("inf")):
                        best[link] = new_cost
                        if self._file_exists(link):
                            heapq.heappush(heap, (new_cost, depth + 1, link))
                        elif link not in self.page_metadata:
                            self.graph.add_node(link)
                            self.page_metadata[link] = {
                                "title": f"{link} (not found)",
                                "description": "Page file does not exist.",
                            }
            else:
                self.page_metadata[page] = {
                    "title": f"{page} (not found)",
                    "description": "Page file does not exist.",
                }

        return self.graph

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _filepath(self, name: str) -> str:
        return os.path.join(self.pages_dir, f"{name}.txt")

    def _file_exists(self, name: str) -> bool:
        return os.path.exists(self._filepath(name))
