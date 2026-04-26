"""
gui.py
------
Tkinter GUI for the Web Crawler & Link Graph Analyzer.

Layout (single window, notebook tabs):
  Tab 1 – Crawl          : choose root, run BFS crawl, see discovery order
  Tab 2 – Graph Info     : node list, in/out degrees, dangling / self-loops
  Tab 3 – SCCs           : Kosaraju's result, which pages share a cycle
  Tab 4 – Topo Sort      : condensation DAG topological order
  Tab 5 – Hubs           : top pages by in-degree (bar-style display)
  Tab 6 – PageRank       : ranked table after 10 power-iteration steps
  Tab 7 – Complexity     : Big-O summary for every algorithm used

Design philosophy: clean monochrome-accent scheme, monospace text for data,
clear headings, no clutter. Runs on vanilla Tkinter (no third-party GUI deps).
"""

import math
import os
import random
import tkinter as tk
from tkinter import ttk, messagebox

from src.crawler import WebCrawler
from src.algorithms import (
    kosaraju_scc,
    condense_graph,
    topological_sort,
    find_hubs,
    pagerank,
    dijkstra,
    reconstruct_path,
)

# ── Colour palette ────────────────────────────────────────────────────
BG       = "#0f0f0f"
PANEL    = "#1a1a1a"
ACCENT   = "#00d4aa"
ACCENT2  = "#0099ff"
TEXT     = "#e8e8e8"
MUTED    = "#888888"
GOOD     = "#44cc88"
WARN     = "#ffaa33"
MONO     = ("Courier New", 10)
HEAD     = ("Courier New", 12, "bold")
TITLE_F  = ("Courier New", 14, "bold")


def styled_text(parent, height=20, width=80) -> tk.Text:
    """Return a pre-styled read-only Text widget."""
    t = tk.Text(
        parent,
        bg=PANEL, fg=TEXT,
        font=MONO,
        insertbackground=ACCENT,
        selectbackground=ACCENT,
        relief="flat",
        bd=0,
        height=height,
        width=width,
        wrap="word",
        state="disabled",
    )
    # Colour tags
    t.tag_configure("accent",  foreground=ACCENT,  font=("Courier New", 10, "bold"))
    t.tag_configure("accent2", foreground=ACCENT2, font=("Courier New", 10, "bold"))
    t.tag_configure("good",    foreground=GOOD)
    t.tag_configure("warn",    foreground=WARN)
    t.tag_configure("muted",   foreground=MUTED)
    t.tag_configure("head",    foreground=ACCENT,  font=HEAD)
    t.tag_configure("title",   foreground=ACCENT,  font=TITLE_F)
    return t


def write(widget: tk.Text, *parts):
    """
    Write to a styled Text widget.
    `parts` alternates between (text, tag) pairs OR plain strings.

    Usage:
        write(w, "normal text")
        write(w, "colored text", "accent", "  more normal")
    """
    widget.config(state="normal")
    i = 0
    while i < len(parts):
        text = parts[i]
        tag  = parts[i + 1] if (i + 1 < len(parts) and isinstance(parts[i + 1], str)
                                  and not parts[i + 1].startswith("\n")
                                  and len(parts[i + 1]) < 20
                                  and i + 1 < len(parts)
                                  and _is_tag(parts[i + 1])) else None
        if tag:
            widget.insert("end", text, tag)
            i += 2
        else:
            widget.insert("end", text)
            i += 1
    widget.config(state="disabled")


def _is_tag(s):
    return s in ("accent", "accent2", "good", "warn", "muted", "head", "title")


def clear(widget: tk.Text):
    widget.config(state="normal")
    widget.delete("1.0", "end")
    widget.config(state="disabled")


# ======================================================================
# Main Application
# ======================================================================

class App(tk.Tk):
    def __init__(self, pages_dir: str):
        super().__init__()
        self.pages_dir = pages_dir
        self.crawler   = WebCrawler(pages_dir)
        self.graph     = None
        self.sccs      = None
        self.pr        = None

        self._viz_seed = 42      # seed for spring layout; REDRAW changes this

        self.title("🕸  Web Crawler & Link Graph Analyzer")
        self.configure(bg=BG)
        self.geometry("960x680")
        self.resizable(True, True)

        self._build_header()
        self._build_notebook()
        self._build_statusbar()

    # ── Header ────────────────────────────────────────────────────────

    def _build_header(self):
        hdr = tk.Frame(self, bg=BG)
        hdr.pack(fill="x", padx=16, pady=(14, 0))

        tk.Label(
            hdr, text="WEB CRAWLER  &  LINK GRAPH ANALYZER",
            bg=BG, fg=ACCENT, font=("Courier New", 15, "bold")
        ).pack(side="left")

        tk.Label(
            hdr, text="BFS · Kosaraju SCC · PageRank · TopoSort · Dijkstra · Spring Layout",
            bg=BG, fg=MUTED, font=("Courier New", 9)
        ).pack(side="right", pady=6)

        tk.Frame(self, bg=ACCENT, height=1).pack(fill="x", padx=16, pady=(6, 0))

    # ── Notebook tabs ─────────────────────────────────────────────────

    def _build_notebook(self):
        style = ttk.Style(self)
        style.theme_use("default")
        style.configure("TNotebook",        background=BG,    borderwidth=0)
        style.configure("TNotebook.Tab",    background=PANEL, foreground=MUTED,
                        font=("Courier New", 9, "bold"), padding=[10, 4])
        style.map("TNotebook.Tab",
                  background=[("selected", ACCENT)],
                  foreground=[("selected", BG)])

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=16, pady=10)

        self._tab_crawl(nb)
        self._tab_graph(nb)
        self._tab_visualize(nb)
        self._tab_scc(nb)
        self._tab_topo(nb)
        self._tab_hubs(nb)
        self._tab_pagerank(nb)
        self._tab_shortest_path(nb)
        self._tab_complexity(nb)

    # ── Status bar ────────────────────────────────────────────────────

    def _build_statusbar(self):
        self._status_var = tk.StringVar(value="Ready.  Select a root page and click  [ RUN CRAWLER ]")
        bar = tk.Label(self, textvariable=self._status_var,
                       bg=PANEL, fg=MUTED, font=("Courier New", 8),
                       anchor="w", padx=10, pady=4)
        bar.pack(fill="x", side="bottom")

    def _set_status(self, msg: str):
        self._status_var.set(msg)

    # ==================================================================
    # TAB 1 — CRAWL
    # ==================================================================

    def _tab_crawl(self, nb):
        frame = tk.Frame(nb, bg=BG)
        nb.add(frame, text="  CRAWL  ")

        # Controls row
        ctrl = tk.Frame(frame, bg=BG)
        ctrl.pack(fill="x", padx=12, pady=10)

        tk.Label(ctrl, text="Root page:", bg=BG, fg=TEXT,
                 font=MONO).pack(side="left")

        # Populate dropdown from available pages
        page_names = sorted(
            f.replace(".txt", "")
            for f in os.listdir(self.pages_dir)
            if f.endswith(".txt")
        )
        self._root_var = tk.StringVar(value="home")
        cb = ttk.Combobox(ctrl, textvariable=self._root_var,
                          values=page_names, width=18,
                          font=MONO, state="readonly")
        cb.pack(side="left", padx=8)

        btn = tk.Button(
            ctrl, text="[ RUN CRAWLER ]",
            bg=ACCENT, fg=BG, font=("Courier New", 10, "bold"),
            relief="flat", bd=0, padx=12, pady=4,
            activebackground=GOOD, cursor="hand2",
            command=self._run_crawl
        )
        btn.pack(side="left", padx=6)

        # Output
        out_frame = tk.Frame(frame, bg=BG)
        out_frame.pack(fill="both", expand=True, padx=12)

        self._crawl_text = styled_text(out_frame, height=28)
        self._crawl_text.pack(fill="both", expand=True)
        sb = ttk.Scrollbar(out_frame, command=self._crawl_text.yview)
        self._crawl_text.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")

        self._show_crawl_intro()

    def _show_crawl_intro(self):
        t = self._crawl_text
        clear(t)
        write(t, "  WEB CRAWLER — BFS TRAVERSAL\n\n", "title")
        write(t, "  Algorithm : Breadth-First Search (BFS)\n", "muted")
        write(t, "  Complexity : O(V + E)  where V = pages, E = links\n\n", "muted")
        write(t, "  Pages directory : ", "muted")
        write(t, f"{self.pages_dir}\n\n", "accent")
        write(t, "  Select a root page and click [ RUN CRAWLER ] to begin.\n", "muted")

    def _run_crawl(self):
        root = self._root_var.get().strip()
        if not root:
            messagebox.showerror("Error", "Please enter a root page name.")
            return
        try:
            self.graph = self.crawler.crawl(root)
            self.sccs  = kosaraju_scc(self.graph)
            self.pr    = pagerank(self.graph)
        except FileNotFoundError as e:
            messagebox.showerror("File Not Found", str(e))
            return

        t = self._crawl_text
        clear(t)
        write(t, "  BFS CRAWL RESULTS\n", "title")
        write(t, f"  Root         : {root}\n", "accent")
        write(t, f"  Pages found  : {self.graph.num_nodes()}\n")
        write(t, f"  Total links  : {self.graph.num_edges()}\n\n")

        write(t, "  ── Discovery Order (BFS) ─────────────────────────────\n\n", "head")
        for step, page in enumerate(self.crawler.crawl_order, 1):
            meta  = self.crawler.page_metadata.get(page, {})
            title = meta.get("title", page)
            write(t, f"  {step:>3}. ")
            write(t, f"{page:<20}", "accent")
            write(t, f"  →  {title}\n", "muted")

        write(t, "\n  ── Edge Cases Detected ──────────────────────────────\n\n", "head")
        dangling = self.graph.dangling_nodes()
        loops    = self.graph.self_loops()
        if dangling:
            write(t, f"  Dangling pages (no outgoing links): ", "warn")
            write(t, ", ".join(dangling) + "\n")
        else:
            write(t, "  No dangling pages found.\n", "good")

        if loops:
            write(t, f"  Self-links detected: ", "warn")
            write(t, ", ".join(loops) + "\n")
        else:
            write(t, "  No self-links found.\n", "good")

        self._set_status(
            f"Crawl complete — {self.graph.num_nodes()} pages, "
            f"{self.graph.num_edges()} edges.  Explore the other tabs."
        )
        self._refresh_all_tabs()

    # ==================================================================
    # TAB 2 — GRAPH INFO
    # ==================================================================

    def _tab_graph(self, nb):
        frame = tk.Frame(nb, bg=BG)
        nb.add(frame, text="  GRAPH  ")
        self._graph_text = styled_text(frame, height=30)
        self._graph_text.pack(fill="both", expand=True, padx=12, pady=10)
        write(self._graph_text, "  Run the crawler first.\n", "muted")

    def _refresh_graph_tab(self):
        if not self.graph:
            return
        t = self._graph_text
        clear(t)
        write(t, "  ADJACENCY LIST & DEGREE TABLE\n\n", "title")
        write(t, f"  {'PAGE':<22} {'IN':>4}  {'OUT':>4}  {'LINKS TO'}\n", "head")
        write(t, "  " + "─" * 70 + "\n", "muted")

        for node in sorted(self.graph.nodes()):
            ind  = self.graph.in_degree(node)
            outd = self.graph.out_degree(node)
            nbrs = ", ".join(sorted(self.graph.successors(node))) or "—"
            flags = ""
            if self.graph.is_dangling(node):
                flags += " [dangling]"
            if node in self.graph.self_loops():
                flags += " [self-loop]"
            write(t, f"  {node:<22} {ind:>4}  {outd:>4}  ")
            write(t, f"{nbrs}", "accent2")
            if flags:
                write(t, flags, "warn")
            write(t, "\n")

    # ==================================================================
    # TAB 3 — VISUALIZE  (force-directed graph drawing)
    # ==================================================================

    def _tab_visualize(self, nb):
        frame = tk.Frame(nb, bg=BG)
        nb.add(frame, text="  VISUALIZE  ")

        ctrl = tk.Frame(frame, bg=BG)
        ctrl.pack(fill="x", padx=12, pady=(8, 4))

        tk.Label(ctrl,
                 text="Force-directed spring layout  ·  nodes = pages, arrows = links",
                 bg=BG, fg=MUTED, font=("Courier New", 8)).pack(side="left")

        tk.Button(
            ctrl, text="[ REDRAW ]",
            bg=PANEL, fg=ACCENT, font=("Courier New", 9, "bold"),
            relief="flat", bd=0, padx=10, pady=3,
            activebackground=ACCENT, activeforeground=BG,
            cursor="hand2", command=self._redraw_graph
        ).pack(side="right")

        self._viz_canvas = tk.Canvas(frame, bg=BG, highlightthickness=0)
        self._viz_canvas.pack(fill="both", expand=True, padx=12, pady=(0, 10))

        # Redraw whenever the canvas is resized (e.g. window resize)
        self._viz_canvas.bind("<Configure>", lambda _e: self._draw_graph())

    def _redraw_graph(self):
        """Pick a new random seed and redraw the layout."""
        self._viz_seed = random.randint(0, 99_999)
        self._draw_graph()

    def _spring_layout(self, nodes: list, edges: list, W: float, H: float) -> dict:
        """
        Fruchterman-Reingold force-directed layout.

        Repulsive force between every pair: Fr = k²/d
        Attractive force along each edge:  Fa = d²/k
        Temperature cools linearly so the layout stabilises.

        Time: O(iterations × (V² + E))   — fast for V ≤ ~200
        """
        N = len(nodes)
        if N == 0:
            return {}
        if N == 1:
            return {nodes[0]: (W / 2, H / 2)}

        rng = random.Random(self._viz_seed)
        pos = {n: [rng.uniform(W * 0.15, W * 0.85),
                   rng.uniform(H * 0.15, H * 0.85)]
               for n in nodes}

        k = 0.80 * math.sqrt(W * H / N)   # optimal inter-node distance
        edge_set = set(edges)

        for step in range(90):
            disp = {n: [0.0, 0.0] for n in nodes}

            # Repulsion: all pairs push apart
            for i, u in enumerate(nodes):
                for v in nodes[i + 1:]:
                    dx = pos[u][0] - pos[v][0]
                    dy = pos[u][1] - pos[v][1]
                    d = max(math.hypot(dx, dy), 0.01)
                    fr = k * k / d
                    disp[u][0] += fr * dx / d;  disp[u][1] += fr * dy / d
                    disp[v][0] -= fr * dx / d;  disp[v][1] -= fr * dy / d

            # Attraction: edges pull nodes together (treat as undirected)
            seen: set = set()
            for u, v in edge_set:
                key = (min(u, v), max(u, v))
                if key in seen:
                    continue
                seen.add(key)
                dx = pos[v][0] - pos[u][0]
                dy = pos[v][1] - pos[u][1]
                d = max(math.hypot(dx, dy), 0.01)
                fa = d * d / k
                disp[u][0] += fa * dx / d;  disp[u][1] += fa * dy / d
                disp[v][0] -= fa * dx / d;  disp[v][1] -= fa * dy / d

            # Cooling schedule
            temp = k * max(0.05, 1.0 - step / 75)
            pad  = 55
            for n in nodes:
                dx, dy = disp[n]
                d = max(math.hypot(dx, dy), 0.01)
                delta = min(d, temp)
                pos[n][0] = max(pad, min(W - pad, pos[n][0] + delta * dx / d))
                pos[n][1] = max(pad, min(H - pad, pos[n][1] + delta * dy / d))

        return {n: (pos[n][0], pos[n][1]) for n in nodes}

    def _draw_graph(self):
        """Compute spring layout and render the graph on the canvas."""
        canvas = self._viz_canvas
        W = canvas.winfo_width()
        H = canvas.winfo_height()
        if W <= 1 or H <= 1:
            return       # widget not yet laid out — skip

        canvas.delete("all")

        if not self.graph or self.graph.num_nodes() == 0:
            canvas.create_text(W // 2, H // 2,
                                text="Run the crawler first.",
                                fill=MUTED, font=HEAD)
            return

        nodes     = list(self.graph.nodes())
        all_edges = [(s, d) for s in nodes for d in self.graph.successors(s) if s != d]
        edge_set  = set(all_edges)

        # Node classification
        in_cycle: set[str] = set()
        if self.sccs:
            for scc in self.sccs:
                if len(scc) > 1:
                    in_cycle.update(scc)
        dangling_set = set(self.graph.dangling_nodes())

        pos = self._spring_layout(nodes, all_edges, W, H)
        R   = 22   # node radius in pixels

        # ── Draw edges ───────────────────────��────────────────────────
        for src, dst in all_edges:
            if src not in pos or dst not in pos:
                continue
            x1, y1 = pos[src]
            x2, y2 = pos[dst]
            dx, dy = x2 - x1, y2 - y1
            d = max(math.hypot(dx, dy), 0.01)

            # Arrow starts/ends at the circle boundary
            sx = x1 + R * dx / d
            sy = y1 + R * dy / d
            ex = x2 - (R + 4) * dx / d
            ey = y2 - (R + 4) * dy / d

            # Offset bidirectional edges so they don't overlap
            if (dst, src) in edge_set:
                sign  = 1 if src < dst else -1
                ox    = -dy / d * 7 * sign
                oy    =  dx / d * 7 * sign
            else:
                ox, oy = 0.0, 0.0

            canvas.create_line(
                sx + ox, sy + oy, ex + ox, ey + oy,
                fill="#3a3a3a", arrow="last", arrowshape=(9, 11, 3), width=1
            )

            # Edge weight label at midpoint
            w  = self.graph.get_weight(src, dst)
            mx = (sx + ex) / 2 + ox
            my = (sy + ey) / 2 + oy
            canvas.create_text(mx, my, text=f"{w:.0f}",
                               fill="#555555", font=("Courier New", 7))

        # ── Draw nodes (on top of edges) ──────────────────────────────
        for node in nodes:
            if node not in pos:
                continue
            x, y = pos[node]

            if node in in_cycle:
                fill_c, ring_c = "#0a2010", GOOD
            elif node in dangling_set:
                fill_c, ring_c = "#221400", WARN
            else:
                fill_c, ring_c = "#001510", ACCENT

            canvas.create_oval(x - R, y - R, x + R, y + R,
                               fill=fill_c, outline=ring_c, width=2)
            canvas.create_text(x, y, text=node,
                               fill=TEXT, font=("Courier New", 7, "bold"))

        # ── Legend ────────────────────────────────────────────────────
        legend = [
            (ACCENT, "regular page"),
            (WARN,   "dangling (no outlinks)"),
            (GOOD,   "in a cycle (SCC)"),
        ]
        lx = 14
        ly = H - 14 - len(legend) * 20
        for i, (color, label) in enumerate(legend):
            y = ly + i * 20
            canvas.create_oval(lx, y, lx + 12, y + 12,
                               fill="#1a1a1a", outline=color, width=2)
            canvas.create_text(lx + 18, y + 6, text=label,
                               fill=MUTED, font=("Courier New", 8), anchor="w")

    # ==================================================================
    # TAB 4 — SCCs  (Kosaraju)
    # ==================================================================

    def _tab_scc(self, nb):
        frame = tk.Frame(nb, bg=BG)
        nb.add(frame, text="  SCCs  ")
        self._scc_text = styled_text(frame, height=30)
        self._scc_text.pack(fill="both", expand=True, padx=12, pady=10)
        write(self._scc_text, "  Run the crawler first.\n", "muted")

    def _refresh_scc_tab(self):
        if not self.sccs:
            return
        t = self._scc_text
        clear(t)
        write(t, "  STRONGLY CONNECTED COMPONENTS — Kosaraju's Algorithm\n\n", "title")
        write(t, "  Algorithm : Kosaraju's Two-Pass DFS\n", "muted")
        write(t, "  Complexity: O(V + E)\n\n", "muted")
        write(t, "  An SCC is a maximal set of pages where every page\n")
        write(t, "  is reachable from every other page via directed links.\n\n")

        non_trivial = [s for s in self.sccs if len(s) > 1]
        trivial     = [s for s in self.sccs if len(s) == 1]

        write(t, f"  Total SCCs found     : {len(self.sccs)}\n")
        write(t, f"  Multi-node SCCs      : ", "accent")
        write(t, f"{len(non_trivial)}\n")
        write(t, f"  Single-node SCCs     : {len(trivial)}\n\n")

        write(t, "  ── Multi-Node SCCs (Cycles in the web) ──────────────\n\n", "head")
        if non_trivial:
            for idx, comp in enumerate(non_trivial, 1):
                write(t, f"  SCC #{idx}  ({len(comp)} pages)\n", "accent")
                for pg in sorted(comp):
                    write(t, f"    ◉ {pg}\n", "good")
                write(t, "\n")
        else:
            write(t, "  None — no cycles detected in this web.\n", "muted")

        write(t, "  ── Single-Node SCCs ──────────────────────────────────\n\n", "head")
        names = [s[0] for s in trivial]
        for i in range(0, len(names), 5):
            chunk = names[i:i+5]
            write(t, "  " + "  ".join(f"{n:<18}" for n in chunk) + "\n", "muted")

    # ==================================================================
    # TAB 4 — TOPO SORT
    # ==================================================================

    def _tab_topo(self, nb):
        frame = tk.Frame(nb, bg=BG)
        nb.add(frame, text="  TOPO SORT  ")
        self._topo_text = styled_text(frame, height=30)
        self._topo_text.pack(fill="both", expand=True, padx=12, pady=10)
        write(self._topo_text, "  Run the crawler first.\n", "muted")

    def _refresh_topo_tab(self):
        if not self.graph or not self.sccs:
            return
        t = self._topo_text
        clear(t)
        write(t, "  TOPOLOGICAL SORT OF CONDENSATION DAG\n\n", "title")
        write(t, "  Algorithm : Kahn's BFS-based Topological Sort\n", "muted")
        write(t, "  Complexity: O(V + E)\n\n", "muted")
        write(t,
              "  We first condense the graph: each SCC becomes one super-node.\n"
              "  The result is a DAG.  Topological order shows which\n"
              "  clusters of pages 'come before' others in link hierarchy.\n\n")

        node_to_scc, dag = condense_graph(self.graph, self.sccs)
        order = topological_sort(dag)

        write(t, "  ── Condensation DAG ──────────────────────────────────\n\n", "head")
        for scc_label in order:
            idx   = int(scc_label.split("_")[1])
            pages = sorted(self.sccs[idx])
            write(t, f"  {scc_label:<10}", "accent")
            write(t, "  →  " + ", ".join(pages) + "\n")

        write(t, "\n  ── Topological Order (processing sequence) ───────────\n\n", "head")
        for step, label in enumerate(order, 1):
            idx   = int(label.split("_")[1])
            pages = sorted(self.sccs[idx])
            write(t, f"  {step:>3}. {label:<10}", "accent2")
            write(t, "  " + ", ".join(pages) + "\n")

    # ==================================================================
    # TAB 5 — HUBS
    # ==================================================================

    def _tab_hubs(self, nb):
        frame = tk.Frame(nb, bg=BG)
        nb.add(frame, text="  HUBS  ")
        self._hubs_text = styled_text(frame, height=30)
        self._hubs_text.pack(fill="both", expand=True, padx=12, pady=10)
        write(self._hubs_text, "  Run the crawler first.\n", "muted")

    def _refresh_hubs_tab(self):
        if not self.graph:
            return
        t = self._hubs_text
        clear(t)
        write(t, "  HUB PAGES — Highest In-Degree\n\n", "title")
        write(t, "  In-degree = number of OTHER pages that link HERE.\n")
        write(t, "  High in-degree ≈ important / well-referenced page.\n\n")

        hubs   = find_hubs(self.graph, top_n=len(self.graph.nodes()))
        max_in = hubs[0][1] if hubs else 1

        write(t, f"  {'RANK':<6} {'PAGE':<22} {'IN-DEG':>7}  BAR\n", "head")
        write(t, "  " + "─" * 60 + "\n", "muted")

        for rank, (page, deg) in enumerate(hubs, 1):
            bar_len  = int((deg / max(max_in, 1)) * 30)
            bar      = "█" * bar_len
            color    = "accent" if rank <= 3 else ("accent2" if rank <= 8 else "muted")
            write(t, f"  {rank:<6} {page:<22} {deg:>7}  ")
            write(t, bar + "\n", color)

    # ==================================================================
    # TAB 6 — PAGERANK
    # ==================================================================

    def _tab_pagerank(self, nb):
        frame = tk.Frame(nb, bg=BG)
        nb.add(frame, text="  PAGERANK  ")
        self._pr_text = styled_text(frame, height=30)
        self._pr_text.pack(fill="both", expand=True, padx=12, pady=10)
        write(self._pr_text, "  Run the crawler first.\n", "muted")

    def _refresh_pr_tab(self):
        if not self.pr:
            return
        t = self._pr_text
        clear(t)
        write(t, "  PAGERANK — Simplified Power Iteration\n\n", "title")
        write(t, "  Formula  : PR(u) = (1-d)/N  +  d * Σ PR(v)/out(v)\n", "muted")
        write(t, "  Settings : damping d = 0.85,  iterations = 10\n", "muted")
        write(t, "  Complexity: O(k·(V+E))  where k = iterations\n\n", "muted")

        ranked = sorted(self.pr.items(), key=lambda x: x[1], reverse=True)
        max_pr = ranked[0][1] if ranked else 1.0

        write(t, f"  {'RANK':<6} {'PAGE':<22} {'SCORE':>9}  BAR\n", "head")
        write(t, "  " + "─" * 65 + "\n", "muted")

        for rank, (page, score) in enumerate(ranked, 1):
            bar_len = int((score / max_pr) * 28)
            bar     = "█" * bar_len
            color   = "accent" if rank <= 3 else ("accent2" if rank <= 8 else "muted")
            write(t, f"  {rank:<6} {page:<22} {score:>9.6f}  ")
            write(t, bar + "\n", color)

    # ==================================================================
    # TAB 7 — SHORTEST PATH (Dijkstra)
    # ==================================================================

    def _tab_shortest_path(self, nb):
        frame = tk.Frame(nb, bg=BG)
        nb.add(frame, text="  SHORTEST PATH  ")

        ctrl = tk.Frame(frame, bg=BG)
        ctrl.pack(fill="x", padx=12, pady=10)

        page_names = sorted(
            f.replace(".txt", "")
            for f in os.listdir(self.pages_dir)
            if f.endswith(".txt")
        )

        tk.Label(ctrl, text="Source:", bg=BG, fg=TEXT, font=MONO).pack(side="left")
        self._sp_src_var = tk.StringVar(value="home")
        self._sp_src_cb = ttk.Combobox(
            ctrl, textvariable=self._sp_src_var,
            values=page_names, width=16, font=MONO, state="readonly"
        )
        self._sp_src_cb.pack(side="left", padx=8)

        tk.Label(ctrl, text="Destination:", bg=BG, fg=TEXT, font=MONO).pack(side="left", padx=(8, 0))
        self._sp_dst_var = tk.StringVar(value="contact")
        self._sp_dst_cb = ttk.Combobox(
            ctrl, textvariable=self._sp_dst_var,
            values=page_names, width=16, font=MONO, state="readonly"
        )
        self._sp_dst_cb.pack(side="left", padx=8)

        tk.Button(
            ctrl, text="[ FIND PATH ]",
            bg=ACCENT2, fg=BG, font=("Courier New", 10, "bold"),
            relief="flat", bd=0, padx=12, pady=4,
            activebackground=GOOD, cursor="hand2",
            command=self._run_dijkstra
        ).pack(side="left", padx=6)

        out_frame = tk.Frame(frame, bg=BG)
        out_frame.pack(fill="both", expand=True, padx=12)
        self._sp_text = styled_text(out_frame, height=28)
        self._sp_text.pack(fill="both", expand=True)
        sb = ttk.Scrollbar(out_frame, command=self._sp_text.yview)
        self._sp_text.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")

        self._show_sp_intro()

    def _show_sp_intro(self):
        t = self._sp_text
        clear(t)
        write(t, "  DIJKSTRA'S SHORTEST PATH\n\n", "title")
        write(t, "  Algorithm  : Dijkstra with Min-Heap Priority Queue\n", "muted")
        write(t, "  Complexity : O((V + E) log V)\n\n", "muted")
        write(t, "  Each link has a traversal cost (weight).\n")
        write(t, "  Dijkstra finds the path with the minimum total cost,\n")
        write(t, "  which may differ from the fewest-hops path that BFS finds.\n\n")
        write(t, "  Select source and destination, then click [ FIND PATH ].\n", "muted")

    def _run_dijkstra(self):
        if not self.graph:
            messagebox.showwarning("No Graph", "Run the crawler first.")
            return

        src = self._sp_src_var.get().strip()
        dst = self._sp_dst_var.get().strip()
        if not src or not dst:
            messagebox.showerror("Error", "Select both source and destination.")
            return

        dist, prev = dijkstra(self.graph, src)
        path = reconstruct_path(prev, src, dst)

        t = self._sp_text
        clear(t)
        write(t, "  DIJKSTRA'S SHORTEST PATH RESULT\n\n", "title")
        write(t, "  Source      : ", "muted"); write(t, f"{src}\n", "accent")
        write(t, "  Destination : ", "muted"); write(t, f"{dst}\n\n", "accent")

        if path is None:
            write(t, "  No path exists — destination is not reachable from source.\n", "warn")
            self._set_status(f"Dijkstra: {src} → {dst}  |  unreachable")
            return

        total = dist[dst]

        write(t, "  ── Shortest Path ─────────────────────────────────────\n\n", "head")
        write(t, "  " + " → ".join(path) + "\n\n", "accent")
        write(t, "  Total cost : ", "muted")
        write(t, f"{total:.2f}\n", "good")
        write(t, f"  Hops       : {len(path) - 1}\n\n", "muted")

        write(t, "  ── Step-by-step ──────────────────────────────────────\n\n", "head")
        write(t, f"  {'STEP':<6} {'FROM':<20} {'TO':<20} {'COST':>6}  {'CUMULATIVE':>10}\n", "head")
        write(t, "  " + "─" * 68 + "\n", "muted")

        cumulative = 0.0
        for i in range(len(path) - 1):
            u, v = path[i], path[i + 1]
            w = self.graph.get_weight(u, v)
            cumulative += w
            write(t, f"  {i+1:<6} {u:<20} {v:<20} {w:>6.2f}  {cumulative:>10.2f}\n")

        write(t, "\n  ── All reachable pages from source ───────────────────\n\n", "head")
        write(t, f"  {'PAGE':<22} {'SHORTEST COST':>14}\n", "head")
        write(t, "  " + "─" * 40 + "\n", "muted")
        for node in sorted(dist, key=dist.get):
            d = dist[node]
            if d == float("inf"):
                write(t, f"  {node:<22} {'unreachable':>14}\n", "muted")
            else:
                color = "accent" if node == dst else ("good" if d < float("inf") else "muted")
                write(t, f"  {node:<22} {d:>14.2f}\n", color)

        write(t, "\n  ── Why Dijkstra beats BFS for weighted graphs ────────\n\n", "head")
        write(t, "  BFS finds the fewest-hops path but ignores edge weights.\n")
        write(t, "  Dijkstra pops the cheapest frontier node from a min-heap,\n")
        write(t, "  guaranteeing the globally optimal cost path.\n\n")
        write(t, "  Min-heap push/pop: O(log V)  per operation\n", "muted")
        write(t, f"  Total: O((V+E) log V) = O(({self.graph.num_nodes()}+{self.graph.num_edges()}) × log {self.graph.num_nodes()})\n", "accent2")

        self._set_status(
            f"Dijkstra: {src} → {dst}  |  cost {total:.2f}  |  {len(path)-1} hop(s)"
        )

    def _refresh_shortest_path_tab(self):
        if not self.graph:
            return
        nodes = sorted(self.graph.nodes())
        self._sp_src_cb["values"] = nodes
        self._sp_dst_cb["values"] = nodes
        if self._sp_src_var.get() not in self.graph.nodes():
            self._sp_src_var.set(nodes[0] if nodes else "")
        if self._sp_dst_var.get() not in self.graph.nodes():
            self._sp_dst_var.set(nodes[-1] if nodes else "")

    # ==================================================================
    # TAB 8 — COMPLEXITY
    # ==================================================================

    def _tab_complexity(self, nb):
        frame = tk.Frame(nb, bg=BG)
        nb.add(frame, text="  COMPLEXITY  ")
        t = styled_text(frame, height=30)
        t.pack(fill="both", expand=True, padx=12, pady=10)
        self._populate_complexity(t)

    def _populate_complexity(self, t):
        clear(t)
        write(t, "  ALGORITHM COMPLEXITY ANALYSIS\n\n", "title")

        rows = [
            ("BFS Crawl",
             "O(V + E)", "O(V)",
             "Visit each page once, traverse each link once."),
            ("DFS (finish order)",
             "O(V + E)", "O(V)",
             "Iterative DFS; stack depth bounded by V."),
            ("Kosaraju SCC",
             "O(V + E)", "O(V + E)",
             "Two full DFS passes + reverse graph construction."),
            ("Graph Condensation",
             "O(V + E)", "O(V + E)",
             "Map each node to SCC; scan all edges once."),
            ("Kahn Topo Sort",
             "O(V + E)", "O(V)",
             "BFS over condensed DAG; each node/edge processed once."),
            ("In-Degree (Hubs)",
             "O(V + E)", "O(V)",
             "Count predecessors; stored during graph build."),
            ("PageRank (k iters)",
             "O(k·(V+E))", "O(V)",
             "k=10 iterations; each scans all edges."),
            ("Dijkstra (min-heap)",
             "O((V+E)logV)", "O(V)",
             "Min-heap relaxes cheapest frontier first; one pop per node."),
        ]

        write(t, f"  {'ALGORITHM':<24} {'TIME':^12} {'SPACE':^8}  EXPLANATION\n", "head")
        write(t, "  " + "─" * 80 + "\n", "muted")

        for algo, time, space, note in rows:
            write(t, f"  {algo:<24} ", "accent")
            write(t, f"{time:^12} ", "good")
            write(t, f"{space:^8}  ", "accent2")
            write(t, note + "\n")

        write(t, "\n\n  NOTATION\n\n", "head")
        write(t, "  V  = number of pages (vertices) in the graph\n")
        write(t, "  E  = number of hyperlinks (directed edges)\n")
        write(t, "  k  = number of PageRank iterations (10 here)\n\n")

        write(t, "  OVERALL PIPELINE\n\n", "head")
        write(t, "  The full analysis pipeline runs in  ", "muted")
        write(t, "O(V + E)", "accent")
        write(t, "  (dominated by BFS + SCC).\n", "muted")
        write(t, "  PageRank adds a constant factor of 10,\n  which is negligible for V ≤ 10⁶.\n", "muted")

    # ==================================================================
    # Refresh helpers
    # ==================================================================

    def _refresh_all_tabs(self):
        self._refresh_graph_tab()
        self._draw_graph()
        self._refresh_scc_tab()
        self._refresh_topo_tab()
        self._refresh_hubs_tab()
        self._refresh_pr_tab()
        self._refresh_shortest_path_tab()
