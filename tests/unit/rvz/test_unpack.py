import struct
import unittest

from wiithon.crypto.layout import BLOCK_SIZE
from wiithon.rvz.lfg import SEED_SIZE, LaggedFibonacci
from wiithon.rvz.packing import unpack


class TestUnpack(unittest.TestCase):
    def test_a_copy_token_is_returned_as_is(self):
        raw = struct.pack(">I", 4) + b"ABCD"
        self.assertEqual(unpack(raw, 0), b"ABCD")

    def test_a_generated_run_matches_the_generator(self):
        seed = bytes(range(SEED_SIZE))
        raw = struct.pack(">I", 0x80000000 | 32) + seed

        expected = LaggedFibonacci(seed)
        expected.skip(0x100)

        self.assertEqual(unpack(raw, 0x100), expected.read(32))
        self.assertNotEqual(unpack(raw, 0), unpack(raw, 0x100))

    def test_the_offset_wraps_on_a_block(self):
        seed = bytes(range(SEED_SIZE))
        raw = struct.pack(">I", 0x80000000 | 16) + seed

        self.assertEqual(unpack(raw, 0x40), unpack(raw, BLOCK_SIZE + 0x40))

if __name__ == '__main__':
    unittest.main()