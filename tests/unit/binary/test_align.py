import unittest

from wiithon.binary.align import align


class TestAlign(unittest.TestCase):
    def test_zero_is_already_aligned(self):
        for boundary in (1, 2, 4, 16, 32, 2048, 0x8000):
            with self.subTest(boundary=boundary):
                self.assertEqual(align(0, boundary), 0)

    def test_exact_multiples_are_unchanged(self):
        cases = [(4, 4), (16, 16), (32, 32), (64, 32), (0x8000, 0x8000), (0x10000, 0x8000)]
        for value, boundary in cases:
            with self.subTest(value=value, boundary=boundary):
                self.assertEqual(align(value, boundary), value)

    def test_rounds_up(self):
        cases = [
            (1, 4, 4),
            (3, 4, 4),
            (5, 4, 8),
            (1, 32, 32),
            (31, 32, 32),
            (33, 32, 64),
            (1, 2048, 2048),
            (2049, 2048, 4096),
            (0x7C00, 0x8000, 0x8000),
        ]
        for value, boundary, expected in cases:
            with self.subTest(value=value, boundary=boundary):
                self.assertEqual(align(value, boundary), expected)

    def test_boundary_of_one_is_the_identity(self):
        for value in (0, 1, 7, 12345):
            with self.subTest(value=value):
                self.assertEqual(align(value, 1), value)

    def test_result_is_always_a_multiple_of_the_boundary(self):
        for boundary in (2, 4, 16, 32, 512, 2048):
            for value in range(0, 100):
                with self.subTest(value=value, boundary=boundary):
                    aligned = align(value, boundary)
                    self.assertEqual(aligned % boundary, 0)
                    self.assertGreaterEqual(aligned, value)
                    self.assertLess(aligned - value, boundary)

    def test_large_values(self):
        self.assertEqual(align(0xFFFFFFFF, 0x8000), 0x100000000)
        self.assertEqual(align(4_699_979_776 + 1, 32), 4_699_979_808)


if __name__ == "__main__":
    unittest.main()