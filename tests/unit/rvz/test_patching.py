import unittest

from wiithon.crypto.layout import BLOCK_HEADER_SIZE, SHA1_SIZE
from wiithon.rvz.patching import hash_exceptions

IDENTICAL = bytes(range(256)) * 4


class TestHashExceptions(unittest.TestCase):
    def test_nothing_to_patch(self):
        self.assertEqual(hash_exceptions(IDENTICAL, IDENTICAL), [])

    def test_one_byte_at_the_start(self):
        recomputed = bytearray(IDENTICAL)
        recomputed[0] ^= 0xFF

        found = hash_exceptions(IDENTICAL, bytes(recomputed))

        self.assertEqual(len(found), 1)
        self.assertEqual(found[0], (0, IDENTICAL[:SHA1_SIZE]))

    def test_the_last_byte_is_covered_from_further_back(self):
        recomputed = bytearray(IDENTICAL)
        recomputed[BLOCK_HEADER_SIZE - 1] ^= 0xFF

        found = hash_exceptions(IDENTICAL, bytes(recomputed))

        self.assertEqual(len(found), 1)
        self.assertEqual(found[0][0], BLOCK_HEADER_SIZE - SHA1_SIZE)

    def test_a_whole_header_takes_fifty_two_entries(self):
        recomputed = bytes(byte ^ 0xFF for byte in IDENTICAL)

        self.assertEqual(len(hash_exceptions(IDENTICAL, recomputed)), 52)

    def test_applying_them_reproduces_the_header(self):
        recomputed = bytearray(IDENTICAL)
        for position in (3, 17, 200, 201, 640, 1000, 1023):
            recomputed[position] ^= 0xFF

        patched = bytearray(recomputed)
        for offset, value in hash_exceptions(IDENTICAL, bytes(recomputed)):
            patched[offset:offset + SHA1_SIZE] = value

        self.assertEqual(bytes(patched), IDENTICAL)