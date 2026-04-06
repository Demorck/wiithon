import unittest
from io import BytesIO
import random

from file_helper.yaz0 import Yaz0


class TestYaz0(unittest.TestCase):
    def test_from_data(self):
        data = b"Hello World!"
        yaz = Yaz0.from_data(data)
        self.assertEqual(yaz.magic_word, "Yaz0")
        self.assertEqual(yaz.size, len(data))
        self.assertEqual(yaz.data, data)

    def test_compress_uncompress_roundtrip(self):
        # Create a string with recognizable repetitive patterns
        original_data = b"Yaz0 is an LZ77 variant. Sliding window: back-reference up to 4096 bytes. " * 50
        
        # Compress
        compressed = Yaz0.compress(original_data)
        
        # The compression should significantly reduce the size due to repetitions
        self.assertLess(len(compressed), len(original_data) // 10)
        
        # Uncompress
        uncompressed = Yaz0.uncompress(compressed, len(original_data))
        self.assertEqual(uncompressed, original_data)

    def test_write_read_roundtrip(self):
        original_data = b"Some more random text data that is somewhat repetitive text data repetitive repetitive."
        
        yaz = Yaz0.from_data(original_data)
        out_stream = BytesIO()
        yaz.write(out_stream)
        
        # Reset stream to read
        out_stream.seek(0)
        read_yaz = Yaz0.read(out_stream)
        
        self.assertEqual(read_yaz.magic_word, "Yaz0")
        self.assertEqual(read_yaz.size, len(original_data))
        self.assertEqual(read_yaz.data, original_data)

    def test_empty_data(self):
        data = b""
        yaz = Yaz0.from_data(data)
        out_stream = BytesIO()
        yaz.write(out_stream)
        
        out_stream.seek(0)
        read_yaz = Yaz0.read(out_stream)
        self.assertEqual(read_yaz.data, b"")

    def test_random_data(self):
        # Random data is incompressible, tests the literal fallback without bugs
        random.seed(42)
        # 10 KB of random bytes
        original_data = bytes(random.getrandbits(8) for _ in range(10240))
        
        compressed = Yaz0.compress(original_data)
        # Should be larger due to the group headers and no compression possible
        self.assertGreaterEqual(len(compressed), len(original_data))
        
        uncompressed = Yaz0.uncompress(compressed, len(original_data))
        self.assertEqual(uncompressed, original_data)

if __name__ == "__main__":
    unittest.main()
