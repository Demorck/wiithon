import random
import unittest
from io import BytesIO

from wiithon.exceptions import InvalidFormatError
from wiithon.formats.lz77 import Lz77


def _make_lz77(data: bytes, compression_method: int = 0x10) -> Lz77:
    lz = Lz77()
    lz.magic_word = "LZ77"
    lz.compression_method = compression_method
    lz.data = data
    return lz


class TestLz77Uncompress(unittest.TestCase):
    def test_literals_only(self):
        # flag byte 0x00 -> 8 literals
        compressed = b"\x00" + b"ABCDEFGH"
        self.assertEqual(Lz77.uncompress(compressed, 8), b"ABCDEFGH")

    def test_single_backreference(self):
        # 4 literals "ABCD", then a reference: length 4, distance 4
        # reference = ((4 - 3) << 12) | (4 - 1) = 0x1003
        compressed = b"\x08" + b"ABCD" + b"\x10\x03"
        self.assertEqual(Lz77.uncompress(compressed, 8), b"ABCDABCD")

    def test_overlapping_backreference(self):
        # 1 literal "A", then a reference with distance 1 and length 7 -> RLE
        # reference = ((7 - 3) << 12) | (1 - 1) = 0x4000
        compressed = b"\x40" + b"A" + b"\x40\x00"
        self.assertEqual(Lz77.uncompress(compressed, 8), b"A" * 8)

    def test_stops_at_declared_size(self):
        # The reference asks for 6 bytes but only 2 are needed to reach size
        compressed = b"\x40" + b"A" + b"\x30\x00"
        self.assertEqual(Lz77.uncompress(compressed, 3), b"AAA")

    def test_empty(self):
        self.assertEqual(Lz77.uncompress(b"", 0), b"")


class TestLz77Compress(unittest.TestCase):
    def test_roundtrip_repetitive(self):
        original = b"LZ77 sliding window, back-reference up to 4095 bytes. " * 50

        compressed = Lz77.compress(original)
        # A 18-byte max match over a 54-byte pattern gives roughly 1 byte out
        # for 7 bytes in
        self.assertLess(len(compressed), len(original) // 5)
        self.assertEqual(Lz77.uncompress(compressed, len(original)), original)

    def test_roundtrip_incompressible(self):
        # Random data: no match should be found, every token is a literal
        random.seed(42)
        original = bytes(random.getrandbits(8) for _ in range(10240))

        compressed = Lz77.compress(original)
        # 1 flag byte per 8 literals -> ~12.5% overhead
        self.assertGreater(len(compressed), len(original))
        self.assertEqual(Lz77.uncompress(compressed, len(original)), original)

    def test_roundtrip_single_byte_run(self):
        original = b"A" * 1000
        compressed = Lz77.compress(original)
        self.assertEqual(Lz77.uncompress(compressed, len(original)), original)

    def test_roundtrip_partial_flag_group(self):
        # 3 tokens only: the trailing group must be flushed with the flags
        # left-aligned in the flag byte
        original = b"xyz"
        compressed = Lz77.compress(original)
        self.assertEqual(Lz77.uncompress(compressed, len(original)), original)

    def test_roundtrip_short_inputs(self):
        # Below 3 bytes no match can be encoded, above it the encoder switches
        for size in range(0, 12):
            with self.subTest(size=size):
                original = b"ab" * size
                compressed = Lz77.compress(original)
                self.assertEqual(Lz77.uncompress(compressed, len(original)), original)

    def test_empty(self):
        self.assertEqual(Lz77.compress(b""), b"")

    def test_match_length_is_capped(self):
        # A run longer than the 18-byte buffer must be split into several
        # references, none of them longer than 18
        original = b"B" * 64
        compressed = Lz77.compress(original)
        self.assertEqual(Lz77.uncompress(compressed, len(original)), original)

    def test_distance_fits_in_12_bits(self):
        # A match found at the far end of the 4095-byte window must still be
        # encodable (distance - 1 <= 0xFFF)
        random.seed(7)
        filler = bytes(random.getrandbits(8) for _ in range(4000))
        pattern = b"PATTERN_TO_MATCH"
        original = pattern + filler + pattern

        compressed = Lz77.compress(original)
        self.assertEqual(Lz77.uncompress(compressed, len(original)), original)


class TestLz77FindLongestMatch(unittest.TestCase):
    def test_no_match_when_less_than_3_bytes_left(self):
        data = b"ABCDAB"
        self.assertIsNone(Lz77._find_longest_match(data, 4, 18, 4095))

    def test_no_match_when_nothing_seen_before(self):
        data = b"ABCDEFGH"
        self.assertIsNone(Lz77._find_longest_match(data, 0, 18, 4095))

    def test_exact_distance_and_length(self):
        data = b"ABCD" + b"ABCD"
        self.assertEqual(Lz77._find_longest_match(data, 4, 18, 4095), (4, 4))

    def test_length_capped_by_buffer_size(self):
        data = b"A" * 40
        distance, length = Lz77._find_longest_match(data, 1, 18, 4095)
        self.assertEqual(distance, 1)
        self.assertEqual(length, 18)

    def test_window_size_limits_the_search(self):
        data = b"XYZ" + b"." * 10 + b"XYZ"
        current_position = len(data) - 3
        self.assertIsNone(Lz77._find_longest_match(data, current_position, 18, 5))


class TestLz77ReadWrite(unittest.TestCase):
    def test_write_read_roundtrip(self):
        original = b"Some repetitive text data, repetitive text data, repetitive."

        stream = BytesIO()
        _make_lz77(original).write(stream)

        stream.seek(0)
        read_lz = Lz77.read(stream)

        self.assertEqual(read_lz.magic_word, "LZ77")
        self.assertEqual(read_lz.compression_method, 0x10)
        self.assertEqual(read_lz.size, len(original))
        self.assertEqual(read_lz.data, original)

    def test_write_updates_size_from_data(self):
        lz = _make_lz77(b"0123456789")
        lz.size = 999  # stale value, write() must recompute it

        stream = BytesIO()
        lz.write(stream)

        self.assertEqual(lz.size, 10)
        stream.seek(0)
        self.assertEqual(Lz77.read(stream).size, 10)

    def test_header_layout(self):
        stream = BytesIO()
        _make_lz77(b"ABC", compression_method=0x10).write(stream)

        raw = stream.getvalue()
        self.assertEqual(raw[0:4], b"LZ77")
        # header is little-endian: method in the low byte, size in the high 24 bits
        self.assertEqual(raw[4:8], (0x03 << 8 | 0x10).to_bytes(4, "little"))

    def test_write_read_empty(self):
        stream = BytesIO()
        _make_lz77(b"").write(stream)

        stream.seek(0)
        read_lz = Lz77.read(stream)
        self.assertEqual(read_lz.size, 0)
        self.assertEqual(read_lz.data, b"")

    def test_read_rejects_wrong_magic_word(self):
        stream = BytesIO(b"Yaz0" + b"\x00" * 8)
        with self.assertRaises(InvalidFormatError):
            Lz77.read(stream)


if __name__ == "__main__":
    unittest.main()