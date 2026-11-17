import unittest
import xml.etree.ElementTree as ET

from docs_tools import routing_diagram as rd
from moe_demo.router_sim import N_EXPERTS, TOP_K


class RoutingDiagramTests(unittest.TestCase):
    def test_svg_is_valid_xml(self):
        root = ET.fromstring(rd.build_svg())
        self.assertTrue(root.tag.endswith("svg"))

    def test_selected_experts(self):
        a, b = rd.selected(rd.TOKEN_A), rd.selected(rd.TOKEN_B)
        self.assertEqual(len(a), TOP_K)
        self.assertEqual(len(set(a)), TOP_K)
        self.assertTrue(all(0 <= e < N_EXPERTS for e in a + b))

    def test_tokens_share_no_expert(self):
        # the diagram caption says the two highlighted tokens share no expert
        self.assertFalse(set(rd.selected(rd.TOKEN_A)) & set(rd.selected(rd.TOKEN_B)))

    def test_gates_sum_to_one(self):
        self.assertAlmostEqual(sum(rd.GATES), 1.0)
        self.assertEqual(len(rd.GATES), TOP_K)

    def test_grid_has_all_experts(self):
        svg = rd.build_svg()
        a = rd.selected(rd.TOKEN_A)
        for e in a:
            self.assertIn(f">E{e}<", svg)


if __name__ == "__main__":
    unittest.main()
