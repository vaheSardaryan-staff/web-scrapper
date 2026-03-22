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

import os
from collections import deque
from src.graph import DirectedGraph


def parse_page(filepath: str) -> tuple[str, str, list[str]]:
    """
    Parse a page text file.

    Returns
    -------
    title       : str
    description : str
    links       : list[str]   — names of linked pages (no extension)
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
                links.append(line)

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

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def crawl(self, root: str) -> DirectedGraph:
        """
        BFS crawl starting from `root`.

        Algorithm
        ---------
        1. Enqueue root; mark it visited.
        2. While queue is not empty:
           a. Dequeue page p; record discovery order.
           b. Read p's file; store metadata.
           c. For each link L in p's file:
              - Add edge p -> L in the graph.
              - If L is unvisited AND its file exists: enqueue it.
        3. Return completed graph.

        Complexity: O(V + E)  where V = pages, E = links
        """
        self.graph = DirectedGraph()
        self.crawl_order = []
        self.page_metadata = {}

        visited: set[str] = set()
        queue: deque[str] = deque()

        # Seed BFS
        if not self._file_exists(root):
            raise FileNotFoundError(f"Root page '{root}' not found in {self.pages_dir}")

        queue.append(root)
        visited.add(root)
        self.graph.add_node(root)

        while queue:
            page = queue.popleft()
            self.crawl_order.append(page)

            # Parse the page file (if it exists)
            filepath = self._filepath(page)
            if os.path.exists(filepath):
                title, desc, links = parse_page(filepath)
                self.page_metadata[page] = {"title": title, "description": desc}

                for link in links:
                    self.graph.add_edge(page, link)   # always add edge

                    if link not in visited:
                        visited.add(link)
                        if self._file_exists(link):
                            queue.append(link)
                        else:
                            # Dangling reference — add node but don't crawl it
                            self.graph.add_node(link)
                            self.page_metadata[link] = {
                                "title": f"{link} (not found)",
                                "description": "Page file does not exist."
                            }
            else:
                # Dangling node reached somehow
                self.page_metadata[page] = {
                    "title": f"{page} (not found)",
                    "description": "Page file does not exist."
                }

        return self.graph

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _filepath(self, name: str) -> str:
        return os.path.join(self.pages_dir, f"{name}.txt")

    def _file_exists(self, name: str) -> bool:
        return os.path.exists(self._filepath(name))
