"""
benchmark.py
------------
Empirical performance testing for the Web Crawler & Link Graph Analyzer.

Generates random directed graphs of increasing size, times each algorithm,
and produces matplotlib plots saved to the benchmarks/ directory.

Usage:
    pip install matplotlib
    python benchmark.py
"""

import os
import sys
import random
import time

import matplotlib
matplotlib.use("Agg")                        # non-interactive backend
import matplotlib.pyplot as plt

# ensure project root is importable
sys.path.insert(0, os.path.dirname(__file__))

from src.graph import DirectedGraph
from src.algorithms import (
    dfs_finish_order,
    kosaraju_scc,
    condense_graph,
    topological_sort,
    find_hubs,
    pagerank,
)


# ── Graph generator ──────────────────────────────────────────────────

def generate_random_graph(num_nodes: int, edges_per_node: int = 3) -> DirectedGraph:
    """
    Build a random directed graph with `num_nodes` nodes and
    approximately `num_nodes * edges_per_node` edges.
    """
    g = DirectedGraph()
    node_names = [f"page_{i}" for i in range(num_nodes)]
    for name in node_names:
        g.add_node(name)

    num_edges = num_nodes * edges_per_node
    for _ in range(num_edges):
        src = random.choice(node_names)
        dst = random.choice(node_names)
        g.add_edge(src, dst)

    return g


# ── BFS traversal (standalone for benchmarking) ─────────────────────

def bfs_traversal(graph: DirectedGraph, start: str) -> list[str]:
    """BFS from `start`, returns discovery order."""
    from collections import deque
    visited = {start}
    queue = deque([start])
    order = []
    while queue:
        node = queue.popleft()
        order.append(node)
        for nbr in graph.successors(node):
            if nbr not in visited:
                visited.add(nbr)
                queue.append(nbr)
    return order


# ── Timing helper ────────────────────────────────────────────────────

def time_function(func, *args, runs: int = 5) -> float:
    """Run `func(*args)` multiple times and return the average time in ms."""
    times = []
    for _ in range(runs):
        start = time.perf_counter()
        func(*args)
        elapsed = (time.perf_counter() - start) * 1000   # ms
        times.append(elapsed)
    return sum(times) / len(times)


# ── Main benchmark ───────────────────────────────────────────────────

SIZES = [50, 100, 500, 1_000, 2_000, 5_000]
EDGES_PER_NODE = 3
RUNS = 5

ALGORITHMS = {
    "BFS Traversal":    None,
    "DFS Finish Order": None,
    "Kosaraju SCC":     None,
    "Condensation + Topo Sort": None,
    "PageRank (10 iter)": None,
}


def run_benchmarks():
    results = {name: [] for name in ALGORITHMS}
    random.seed(42)

    print(f"{'V':>6}  {'E':>8}  ", end="")
    for name in ALGORITHMS:
        print(f"{name:>24}", end="")
    print()
    print("-" * 90)

    for V in SIZES:
        graph = generate_random_graph(V, EDGES_PER_NODE)
        E = graph.num_edges()
        root = "page_0"

        # BFS
        t_bfs = time_function(bfs_traversal, graph, root, runs=RUNS)
        results["BFS Traversal"].append(t_bfs)

        # DFS
        def run_dfs():
            visited = set()
            for node in graph.nodes():
                if node not in visited:
                    dfs_finish_order(graph, node, visited)

        t_dfs = time_function(run_dfs, runs=RUNS)
        results["DFS Finish Order"].append(t_dfs)

        # Kosaraju
        t_scc = time_function(kosaraju_scc, graph, runs=RUNS)
        results["Kosaraju SCC"].append(t_scc)

        # Condensation + Topological Sort
        def run_condense_topo():
            sccs = kosaraju_scc(graph)
            _, dag = condense_graph(graph, sccs)
            topological_sort(dag)

        t_topo = time_function(run_condense_topo, runs=RUNS)
        results["Condensation + Topo Sort"].append(t_topo)

        # PageRank
        t_pr = time_function(pagerank, graph, runs=RUNS)
        results["PageRank (10 iter)"].append(t_pr)

        # Print row
        print(f"{V:>6}  {E:>8}  ", end="")
        for name in ALGORITHMS:
            print(f"{results[name][-1]:>22.3f}ms", end="")
        print()

    return results


# ── Plotting ─────────────────────────────────────────────────────────

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "benchmarks")


def plot_results(results: dict):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    colors = {
        "BFS Traversal":            "#00d4aa",
        "DFS Finish Order":         "#0099ff",
        "Kosaraju SCC":             "#ff6b6b",
        "Condensation + Topo Sort": "#ffa940",
        "PageRank (10 iter)":       "#b37feb",
    }

    # ── Plot 1: Linear scale ─────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(10, 6))
    for name, times in results.items():
        ax.plot(SIZES, times, marker="o", linewidth=2, label=name, color=colors[name])

    ax.set_xlabel("Number of Nodes (V)", fontsize=12)
    ax.set_ylabel("Execution Time (ms)", fontsize=12)
    ax.set_title("Algorithm Execution Time vs Graph Size", fontsize=14)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    path1 = os.path.join(OUTPUT_DIR, "execution_time_linear.png")
    fig.savefig(path1, dpi=150)
    plt.close(fig)
    print(f"\nSaved: {path1}")

    # ── Plot 2: Log-log scale (growth rate verification) ─────────────
    fig, ax = plt.subplots(figsize=(10, 6))
    for name, times in results.items():
        ax.loglog(SIZES, times, marker="s", linewidth=2, label=name, color=colors[name])

    # Reference line: O(V) growth
    ref_times = [SIZES[0] * 0.001]   # anchor to smallest measurement
    for i in range(1, len(SIZES)):
        ref_times.append(ref_times[0] * (SIZES[i] / SIZES[0]))
    ax.loglog(SIZES, ref_times, "--", color="gray", linewidth=1.5, label="O(V) reference", alpha=0.7)

    ax.set_xlabel("Number of Nodes (V)", fontsize=12)
    ax.set_ylabel("Execution Time (ms)", fontsize=12)
    ax.set_title("Log-Log Plot — Growth Rate Verification", fontsize=14)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3, which="both")
    fig.tight_layout()

    path2 = os.path.join(OUTPUT_DIR, "execution_time_loglog.png")
    fig.savefig(path2, dpi=150)
    plt.close(fig)
    print(f"Saved: {path2}")

    # ── Plot 3: Per-algorithm subplots ───────────────────────────────
    fig, axes = plt.subplots(2, 3, figsize=(15, 9))
    axes = axes.flatten()

    for i, (name, times) in enumerate(results.items()):
        ax = axes[i]
        ax.plot(SIZES, times, marker="o", linewidth=2, color=colors[name])
        ax.set_title(name, fontsize=11, fontweight="bold")
        ax.set_xlabel("Nodes (V)")
        ax.set_ylabel("Time (ms)")
        ax.grid(True, alpha=0.3)

    # Hide the unused 6th subplot
    axes[5].axis("off")
    fig.suptitle("Individual Algorithm Scaling", fontsize=14, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.95])

    path3 = os.path.join(OUTPUT_DIR, "per_algorithm_scaling.png")
    fig.savefig(path3, dpi=150)
    plt.close(fig)
    print(f"Saved: {path3}")


# ── Entry point ──────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 90)
    print("  Web Crawler — Empirical Performance Benchmark")
    print(f"  Graph sizes: {SIZES}  |  Edges per node: {EDGES_PER_NODE}  |  Runs: {RUNS}")
    print("=" * 90)
    print()

    results = run_benchmarks()
    plot_results(results)

    print("\nDone. All plots saved to benchmarks/")
