import hashlib
import unittest

from wiithon.rvz.lfg import BUFFER_SIZE, SEED_SIZE, LaggedFibonacci

# Known test vectors
SEED = bytes(range(SEED_SIZE))
FIRST_32 = bytes.fromhex(
    "1d757e0b64346456b7f95f37b14dcdec2ea34b4f13ef95cae6a79d4f23ca1813"
)
SECOND_BUFFER_16 = bytes.fromhex("c424b562456ef8de9bd2444983d9744a")
SHA256_32K = "74da5cfcff1933aa159c12e14a845701362e47f0e2ea9df23ea673c18db45a98"


class TestLaggedFibonacci(unittest.TestCase):
    def test_known_vectors(self):
        """Check basic generation and buffer crossing"""
        lfg = LaggedFibonacci(SEED)
        self.assertEqual(lfg.read(32), FIRST_32)

        # Check beyond the first buffer boundary
        lfg = LaggedFibonacci(SEED)
        lfg.skip(BUFFER_SIZE)
        self.assertEqual(lfg.read(16), SECOND_BUFFER_16)

    def test_full_sector_hash(self):
        # 32KB corresponds to the size of an RVZ chunk
        data = LaggedFibonacci(SEED).read(0x8000)
        self.assertEqual(hashlib.sha256(data).hexdigest(), SHA256_32K)

    def test_zero_seed(self):
        """A zero seed must produce an infinite stream of zeros"""
        lfg = LaggedFibonacci(bytes(SEED_SIZE))
        self.assertEqual(lfg.read(4096), bytes(4096))

    def test_duplicated_bits(self):
        """
        Check that bits 22-23 are always equal to bits 24-25
        This is a known quirk of the PRNG
        """
        data = LaggedFibonacci(SEED).read(0x4000)
        for offset in range(0, len(data), 4):
            word = int.from_bytes(data[offset: offset + 4], "big")
            # 0x00C00000 specifically targets these two bits
            self.assertEqual(word & 0x00C00000, (word >> 2) & 0x00C00000)

    def test_chunked_reads(self):
        """Reading the stream in multiple small chunks must not alter the internal state"""
        chunks = [1, 7, 2000, BUFFER_SIZE, 500, 68]

        # read everything at once
        whole_stream = LaggedFibonacci(SEED).read(sum(chunks))

        #  read chunk by chunk
        lfg = LaggedFibonacci(SEED)
        pieces = b"".join(lfg.read(n) for n in chunks)

        self.assertEqual(pieces, whole_stream)

    def test_skip_logic(self):
        """Calling skip() must have the exact same effect as read() and discard"""
        lfg_read = LaggedFibonacci(SEED)
        lfg_skip = LaggedFibonacci(SEED)

        # Advance by discarding read data
        _ = lfg_read.read(BUFFER_SIZE + 100)
        expected = lfg_read.read(200)

        # Advance using skip
        lfg_skip.skip(BUFFER_SIZE + 100)
        actual = lfg_skip.read(200)

        self.assertEqual(actual, expected)


class TestLaggedFibonacciErrors(unittest.TestCase):
    def test_invalid_seed_length(self):
        with self.assertRaises(ValueError):
            LaggedFibonacci(bytes(SEED_SIZE - 1))

        with self.assertRaises(ValueError):
            LaggedFibonacci(bytes(SEED_SIZE + 1))

    def test_negative_counts(self):
        lfg = LaggedFibonacci(SEED)
        with self.assertRaises(ValueError):
            lfg.read(-1)
        with self.assertRaises(ValueError):
            lfg.skip(-10)


if __name__ == '__main__':
    unittest.main()