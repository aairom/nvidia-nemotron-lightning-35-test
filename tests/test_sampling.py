import unittest

from docs_tools import sampling

PS = """  2048 12.5 /Applications/Ollama.app/ollama serve
 10240 98.2 /usr/bin/ollama runner --model x
  5000  1.0 /usr/bin/python other
  bad   x   ollama broken
"""

VM = """Mach Virtual Memory Statistics: (page size of 16384 bytes)
Pages free:                               1000.
Pages active:                             2000.
Pages wired down:                         3000.
"""


class ParserTests(unittest.TestCase):
    def test_parse_ps_sums_only_matching_rows(self):
        rss_mb, cpu = sampling.parse_ps(PS)
        self.assertAlmostEqual(rss_mb, (2048 + 10240) / 1024)
        self.assertAlmostEqual(cpu, 110.7)

    def test_parse_ps_empty(self):
        self.assertEqual(sampling.parse_ps(""), (0.0, 0.0))

    def test_parse_vm_stat(self):
        v = sampling.parse_vm_stat(VM)
        self.assertAlmostEqual(v["wired_gb"], 3000 * 16384 / 1e9)
        self.assertAlmostEqual(v["free_gb"], 1000 * 16384 / 1e9)

    def test_parse_vm_stat_defaults(self):
        v = sampling.parse_vm_stat("garbage")
        self.assertEqual(v["wired_gb"], 0.0)

    def test_take_sample_uses_commands(self):
        calls = []

        def fake(cmd):
            calls.append(cmd[0])
            return PS if cmd[0] == "ps" else VM

        orig = sampling._run
        sampling._run = fake
        try:
            s = sampling.take_sample()
        finally:
            sampling._run = orig
        self.assertEqual(calls, ["ps", "vm_stat"])
        self.assertEqual(set(s), {"cpu_pct", "rss_mb", "wired_gb"})


class SamplerTests(unittest.TestCase):
    def test_collects_samples_and_peak(self):
        seq = iter([{"cpu_pct": 5.0}, {"cpu_pct": 9.0}] + [{"cpu_pct": 1.0}] * 100)
        with sampling.Sampler(interval=0.01, sample_fn=lambda: next(seq)) as s:
            while len(s.samples) < 3:
                pass
        self.assertGreaterEqual(len(s.samples), 3)
        self.assertEqual(s.peak("cpu_pct"), 9.0)
        self.assertEqual(s.peak("missing"), 0.0)

    def test_failing_sampler_does_not_raise(self):
        def boom():
            raise RuntimeError("x")

        with sampling.Sampler(interval=0.01, sample_fn=boom) as s:
            pass
        self.assertEqual(s.samples, [])


if __name__ == "__main__":
    unittest.main()
