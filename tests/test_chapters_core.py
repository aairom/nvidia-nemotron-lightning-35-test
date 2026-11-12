import unittest

from docs_tools import chapters_core
from docs_tools.context import Ctx


class CoreChapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        first = Ctx()
        for fn in (chapters_core.chapter1, chapters_core.chapter2, chapters_core.chapter3, chapters_core.chapter4):
            fn(first)
        cls.first = first

    def render(self, fn):
        ctx = Ctx(self.first.new_labels, strict=True, titles={a: t for _, a, t in self.first.sections})
        return fn(ctx), ctx

    def test_each_chapter_renders_with_heading_and_figures(self):
        for n, fn in enumerate((chapters_core.chapter1, chapters_core.chapter2,
                                chapters_core.chapter3, chapters_core.chapter4), 1):
            html, ctx = self.render(fn)
            self.assertIn(f'id="ch{n}"', html)
            self.assertTrue(ctx.new_labels, f"chapter {n} has no figures")
            self.assertTrue(all(label.startswith(f"Figure {n}-") for label in ctx.new_labels.values()))

    def test_module_roles_cover_every_source_file(self):
        from docs_tools import data
        for rel in data.SOURCE_FILES:
            self.assertTrue(chapters_core._mod_role(rel))

    def test_expert_chapter_states_simulation_honestly(self):
        html, _ = self.render(chapters_core.chapter4)
        self.assertRegex(html.lower(), r"simulat|illustrat")


if __name__ == "__main__":
    unittest.main()
