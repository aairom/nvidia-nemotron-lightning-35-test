import tempfile
import unittest
from pathlib import Path

from PIL import Image

from docs_tools import data
from moe_demo import router_sim
from moe_demo.categories import CATEGORIES


def _run(category, tps, ttft, cold=False):
    return {"category": category, "tps": tps, "ttft_s": ttft, "generated_tokens": 100, "wall_s": 5.0,
            "cold": cold, "load_s": 40.0, "peak_cpu_pct": 100.0, "peak_wired_gb": 25.0}


class FileHelperTests(unittest.TestCase):
    def test_read_text_default_and_line_count(self):
        self.assertEqual(data.read_text("does/not/exist", "dflt"), "dflt")
        self.assertGreater(data.line_count("app.py"), 100)
        self.assertEqual(data.line_count("nope.py"), 0)
        self.assertIn("app.py", data.source_stats())

    def test_snippet(self):
        s = data.snippet("moe_demo/metrics.py", "class ", "def ", max_lines=5)
        self.assertTrue(s.startswith("class "))
        self.assertLessEqual(len(s.splitlines()), 5)
        with self.assertRaises(KeyError):
            data.snippet("moe_demo/metrics.py", "@@missing@@")

    def test_source_of(self):
        self.assertIn("def classify", data.source_of(data.categories.classify))

    def test_count_tests(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "test_a.py").write_text("def test_x(): pass\nclass T:\n    def test_y(self): pass\n    def helper(self): pass\n")
            (Path(d) / "other.py").write_text("def test_z(): pass\n")
            self.assertEqual(data.count_tests(Path(d)), {"test_a.py": 2})

    def test_image_data_uri_resizes(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x.png"
            Image.new("RGBA", (400, 200), (255, 0, 0, 255)).save(p)
            uri = data.image_data_uri(str(p), max_width=100)
            self.assertTrue(uri.startswith("data:image/jpeg;base64,"))

    def test_project_tree_skips_hidden(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "pkg").mkdir()
            (root / "pkg" / "m.py").write_text("")
            (root / ".venv").mkdir()
            (root / "_private").mkdir()
            (root / "a.py").write_text("")
            (root / "x.html").write_text("")
            tree = data.project_tree(root)
            self.assertIn("pkg/", tree)
            self.assertIn("m.py", tree)
            self.assertIn("a.py", tree)
            for hidden in (".venv", "_private", "x.html"):
                self.assertNotIn(hidden, tree)


class BenchmarkDataTests(unittest.TestCase):
    # per_category() iterates every category, so give each one a run; "reasoning" is the 30 tok/s one.
    bench = {"runs": [_run("coding", 40, 9.0, cold=True), _run("coding", 50, 0.5), _run("reasoning", 30, 1.0)]
             + [_run(k, 45, 0.5) for k in CATEGORIES if k not in ("coding", "reasoning")]}

    def test_per_category_excludes_cold_ttft(self):
        pc = data.per_category(self.bench)
        self.assertEqual(pc["coding"]["n"], 2)
        self.assertAlmostEqual(pc["coding"]["tps"], 45)
        self.assertAlmostEqual(pc["coding"]["ttft"], 0.5)

    def test_headline(self):
        h = data.headline(self.bench)
        self.assertEqual(h["runs"], len(self.bench["runs"]))
        self.assertEqual((h["tps_min"], h["tps_max"]), (30, 50))
        self.assertEqual(h["cold_load"], 40.0)
        self.assertAlmostEqual(h["ttft_warm_mean"], (0.5 + 1.0 + 0.5 * (len(CATEGORIES) - 2)) / len(CATEGORIES))
        self.assertEqual(h["gen_total"], 100 * len(self.bench["runs"]))

    def test_load_benchmark_from_file(self):
        b = data.load_benchmark()
        self.assertIn("runs", b)
        self.assertIn("host", b)


class RouterDataTests(unittest.TestCase):
    def test_affinity_matrix_shape(self):
        rows, cols, m = data.affinity_matrix()
        self.assertEqual(len(m), len(rows))
        self.assertEqual(len(m[0]), len(cols))
        self.assertEqual(len(cols), len(CATEGORIES))

    def test_simulated_shares_sum_to_one(self):
        for shares in data.simulated_shares().values():
            self.assertAlmostEqual(sum(shares.values()), 1.0, places=3)

    def test_strength_sweep_monotonic_and_restores(self):
        before = router_sim.AFFINITY_STRENGTH
        rows = data.strength_sweep()
        self.assertEqual(router_sim.AFFINITY_STRENGTH, before)
        tops = [r[1] for r in rows]
        self.assertEqual(tops, sorted(tops))
        self.assertGreater(tops[-1], tops[0])

    def test_classifier_accuracy_all_correct(self):
        res = data.classifier_accuracy()
        self.assertGreaterEqual(len(res), 15)
        self.assertTrue(all(k == pred for k, _, pred in res))

    def test_concentration(self):
        self.assertAlmostEqual(data.concentration({"a": 0.5, "b": 0.3, "c": 0.2}), 0.8)


if __name__ == "__main__":
    unittest.main()
