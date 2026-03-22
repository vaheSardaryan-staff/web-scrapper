"""
Tests for WebCrawler (src/crawler.py).
Uses a temporary directory with small .txt page files.
Run:  python -m pytest tests/
"""

import os
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
        self.assertEqual(links, ["page_a", "page_b"])
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

    def test_missing_link_still_added_as_node(self):
        graph = self.crawler.crawl("page")
        self.assertIn("ghost", graph.nodes())

    def test_missing_link_is_dangling(self):
        graph = self.crawler.crawl("page")
        self.assertTrue(graph.is_dangling("ghost"))

    def test_edge_to_missing_page_exists(self):
        graph = self.crawler.crawl("page")
        self.assertIn("ghost", graph.successors("page"))


if __name__ == "__main__":
    unittest.main()
