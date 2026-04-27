"""
Tests for WebCrawler (src/crawler.py).
Uses a temporary directory with small .txt page files.
Run:  python -m pytest tests/
"""

import os
import shutil
import tempfile
import unittest

from src.crawler import WebCrawler, parse_page


class TestParsePageFunction(unittest.TestCase):
    """Test the standalone parse_page() helper."""

    def test_parse_normal_page(self):
        # Create a temp page file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("TITLE: My Page\n")
            f.write("DESCRIPTION: A test page.\n")
            f.write("LINKS:\n")
            f.write("page_a\n")
            f.write("page_b\n")
            path = f.name

        title, desc, links = parse_page(path)
        self.assertEqual(title, "My Page")
        self.assertEqual(desc, "A test page.")
        self.assertEqual(links, [("page_a", 1.0), ("page_b", 1.0)])
        os.unlink(path)

    def test_parse_page_no_links(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("TITLE: Empty Page\n")
            f.write("DESCRIPTION: No links here.\n")
            f.write("LINKS:\n")
            path = f.name

        title, desc, links = parse_page(path)
        self.assertEqual(title, "Empty Page")
        self.assertEqual(links, [])
        os.unlink(path)

    def test_parse_page_with_explicit_weights(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("TITLE: Weighted\nDESCRIPTION: Has weights.\nLINKS:\npage_a 2.5\npage_b 1.0\n")
            path = f.name

        _, _, links = parse_page(path)
        self.assertEqual(links, [("page_a", 2.5), ("page_b", 1.0)])
        os.unlink(path)


class TestWebCrawler(unittest.TestCase):
    """
    Build a small temporary web:

        alpha -> beta -> gamma
        alpha -> gamma
        gamma  (no outgoing links — dangling)
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

        # alpha.txt — links to beta and gamma
        with open(os.path.join(self.tmpdir, "alpha.txt"), "w") as f:
            f.write("TITLE: Alpha\nDESCRIPTION: Start page.\nLINKS:\nbeta\ngamma\n")

        # beta.txt — links to gamma
        with open(os.path.join(self.tmpdir, "beta.txt"), "w") as f:
            f.write("TITLE: Beta\nDESCRIPTION: Middle page.\nLINKS:\ngamma\n")

        # gamma.txt — no outgoing links (dangling)
        with open(os.path.join(self.tmpdir, "gamma.txt"), "w") as f:
            f.write("TITLE: Gamma\nDESCRIPTION: Dead end.\nLINKS:\n")

        self.crawler = WebCrawler(self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_crawl_finds_all_pages(self):
        graph = self.crawler.crawl("alpha")
        self.assertEqual(graph.num_nodes(), 3)

    def test_bfs_order_starts_with_root(self):
        self.crawler.crawl("alpha")
        self.assertEqual(self.crawler.crawl_order[0], "alpha")

    def test_bfs_discovers_all_pages(self):
        self.crawler.crawl("alpha")
        self.assertEqual(set(self.crawler.crawl_order), {"alpha", "beta", "gamma"})

    def test_edges_are_correct(self):
        graph = self.crawler.crawl("alpha")
        self.assertIn("beta", graph.successors("alpha"))
        self.assertIn("gamma", graph.successors("alpha"))
        self.assertIn("gamma", graph.successors("beta"))

    def test_dangling_page_detected(self):
        graph = self.crawler.crawl("alpha")
        self.assertTrue(graph.is_dangling("gamma"))

    def test_metadata_stored(self):
        self.crawler.crawl("alpha")
        self.assertEqual(self.crawler.page_metadata["alpha"]["title"], "Alpha")

    def test_missing_root_raises_error(self):
        with self.assertRaises(FileNotFoundError):
            self.crawler.crawl("nonexistent")


class TestCrawlerWithMissingLink(unittest.TestCase):
    """Test that a link to a non-existent page is handled gracefully."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        # page.txt links to "ghost" which has no file
        with open(os.path.join(self.tmpdir, "page.txt"), "w") as f:
            f.write("TITLE: Page\nDESCRIPTION: Links to ghost.\nLINKS:\nghost\n")

        self.crawler = WebCrawler(self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_missing_link_still_added_as_node(self):
        graph = self.crawler.crawl("page")
        self.assertIn("ghost", graph.nodes())

    def test_missing_link_is_dangling(self):
        graph = self.crawler.crawl("page")
        self.assertTrue(graph.is_dangling("ghost"))

    def test_edge_to_missing_page_exists(self):
        graph = self.crawler.crawl("page")
        self.assertIn("ghost", graph.successors("page"))


class TestDepthLimitedCrawl(unittest.TestCase):
    """
    Web:  root -> level1a, level1b
          level1a -> level2
          level2  -> level3  (should NOT be crawled at max_depth=2)
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        pages = {
            "root":    "TITLE: Root\nDESCRIPTION: .\nLINKS:\nlevel1a\nlevel1b\n",
            "level1a": "TITLE: L1A\nDESCRIPTION: .\nLINKS:\nlevel2\n",
            "level1b": "TITLE: L1B\nDESCRIPTION: .\nLINKS:\n",
            "level2":  "TITLE: L2\nDESCRIPTION: .\nLINKS:\nlevel3\n",
            "level3":  "TITLE: L3\nDESCRIPTION: .\nLINKS:\n",
        }
        for name, content in pages.items():
            with open(os.path.join(self.tmpdir, f"{name}.txt"), "w") as f:
                f.write(content)
        self.crawler = WebCrawler(self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_unlimited_crawl_finds_all(self):
        graph = self.crawler.crawl("root")
        self.assertEqual(graph.num_nodes(), 5)

    def test_depth_0_finds_only_root(self):
        graph = self.crawler.crawl("root", max_depth=0)
        # root is visited; its links are added as nodes but not crawled
        self.assertIn("root", graph.nodes())
        # depth=0 means no links enqueued
        self.assertEqual(len(self.crawler.crawl_order), 1)

    def test_depth_1_finds_root_and_direct_links(self):
        graph = self.crawler.crawl("root", max_depth=1)
        self.assertIn("root",    self.crawler.crawl_order)
        self.assertIn("level1a", self.crawler.crawl_order)
        self.assertIn("level1b", self.crawler.crawl_order)
        self.assertNotIn("level3", self.crawler.crawl_order)

    def test_depth_2_stops_before_level3(self):
        self.crawler.crawl("root", max_depth=2)
        self.assertIn("level2",    self.crawler.crawl_order)
        self.assertNotIn("level3", self.crawler.crawl_order)

    def test_crawl_depth_dict_populated(self):
        self.crawler.crawl("root")
        self.assertEqual(self.crawler.crawl_depth["root"],   0)
        self.assertEqual(self.crawler.crawl_depth["level1a"], 1)
        self.assertEqual(self.crawler.crawl_depth["level2"],  2)
        self.assertEqual(self.crawler.crawl_depth["level3"],  3)


class TestPriorityCrawl(unittest.TestCase):
    """
    Verify that priority crawl visits cheap pages before expensive ones.

    Graph:  root --8.0--> expensive
            root --1.0--> cheap1 --1.0--> cheap2
    BFS order   : root, expensive, cheap1, cheap2
    Priority order: root, cheap1, cheap2, expensive (total cost 2 < 8)
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        pages = {
            "root":      "TITLE: Root\nDESCRIPTION: .\nLINKS:\nexpensive 8.0\ncheap1 1.0\n",
            "expensive": "TITLE: Expensive\nDESCRIPTION: .\nLINKS:\n",
            "cheap1":    "TITLE: Cheap1\nDESCRIPTION: .\nLINKS:\ncheap2 1.0\n",
            "cheap2":    "TITLE: Cheap2\nDESCRIPTION: .\nLINKS:\n",
        }
        for name, content in pages.items():
            with open(os.path.join(self.tmpdir, f"{name}.txt"), "w") as f:
                f.write(content)
        self.crawler = WebCrawler(self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_priority_crawl_finds_all_pages(self):
        graph = self.crawler.priority_crawl("root")
        self.assertEqual(set(graph.nodes()), {"root", "expensive", "cheap1", "cheap2"})

    def test_cheap_pages_discovered_before_expensive(self):
        self.crawler.priority_crawl("root")
        order = self.crawler.crawl_order
        self.assertLess(order.index("cheap2"), order.index("expensive"))

    def test_costs_recorded(self):
        self.crawler.priority_crawl("root")
        self.assertAlmostEqual(self.crawler.crawl_costs["root"],      0.0)
        self.assertAlmostEqual(self.crawler.crawl_costs["cheap1"],    1.0)
        self.assertAlmostEqual(self.crawler.crawl_costs["cheap2"],    2.0)
        self.assertAlmostEqual(self.crawler.crawl_costs["expensive"], 8.0)

    def test_missing_root_raises(self):
        with self.assertRaises(FileNotFoundError):
            self.crawler.priority_crawl("nonexistent")


if __name__ == "__main__":
    unittest.main()
