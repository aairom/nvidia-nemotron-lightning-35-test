import unittest

from docs_tools import chapters_core, chapters_ops
from docs_tools.context import Ctx

CORE = (chapters_core.chapter1, chapters_core.chapter2, chapters_core.chapter3, chapters_core.chapter4)
OPS = (chapters_ops.chapter5, chapters_ops.chapter6, chapters_ops.chapter7, chapters_ops.chapter8)


class OpsChapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        first = Ctx()
        for fn in CORE + OPS:
            fn(first)
        cls.first = first

    def render(self, fn):
        ctx = Ctx(self.first.new_labels, strict=True, titles={a: t for _, a, t in self.first.sections})
        return fn(ctx), ctx

    def test_each_chapter_renders(self):
        for n, fn in enumerate(OPS, 5):
            html, ctx = self.render(fn)
            self.assertIn(f'id="ch{n}"', html)
            self.assertTrue(all(label.startswith(f"Figure {n}-") for label in ctx.new_labels.values()))

    def test_performance_chapter_uses_measured_benchmark(self):
        from docs_tools import data
        html, _ = self.render(chapters_ops.chapter7)
        mean_tps = f"{data.headline(data.load_benchmark())['tps_mean']:.1f}"
        self.assertIn(mean_tps, html)

    def test_gui_runs_are_complete_records(self):
        self.assertGreaterEqual(len(chapters_ops.GUI_RUNS), 4)
        for run in chapters_ops.GUI_RUNS:
            self.assertEqual(len(run), 7)      # the table renderer unpacks exactly 7 columns


if __name__ == "__main__":
    unittest.main()
