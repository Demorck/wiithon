import hashlib
import struct
import unittest
from io import BytesIO

from wiithon.exceptions import CorruptedDataError, InvalidFormatError
from wiithon.rvz.disc import WiaDisc
from wiithon.rvz.enums import WiaCompression, WiaDiscType
from wiithon.rvz.layout import DISC_SIZE, RVZ_MAGIC_WORD, WIA_MAGIC_WORD
from wiithon.rvz.structs.file_header import WiaHeader


def create_mock_header(magic: bytes = RVZ_MAGIC_WORD, iso_size: int = 0x57058000) -> bytes:
    """Helper to generate a structurally valid header with a correct SHA1 hash"""
    body = (
            magic
            + struct.pack(">II", 0x01000000, 0x00090000)
            + struct.pack(">I", DISC_SIZE)
            + bytes(20)
            + struct.pack(">QQ", iso_size, 0x1000)
    )
    return body + hashlib.sha1(body).digest()


class TestWiaRvzStructures(unittest.TestCase):
    def test_header_parsing(self):
        """Check basic header extraction and format detection (RVZ vs WIA)"""
        rvz_header = WiaHeader.read(BytesIO(create_mock_header()))
        self.assertEqual(rvz_header.iso_file_size, 0x57058000)
        self.assertEqual(rvz_header.wia_file_size, 0x1000)
        self.assertEqual(rvz_header.disc_size, DISC_SIZE)
        self.assertTrue(rvz_header.is_rvz)

        wia_header = WiaHeader.read(BytesIO(create_mock_header(WIA_MAGIC_WORD)))
        self.assertFalse(wia_header.is_rvz)
        self.assertEqual(rvz_header.version, 0x01000000)
        self.assertEqual(rvz_header.version_compatible, 0x00090000)

    def test_header_corruption_checks(self):
        """Ensure we reject unknown magics and tampered data that fail the SHA1 verification"""
        with self.assertRaises(InvalidFormatError):
            WiaHeader.read(BytesIO(create_mock_header(b"WBFS")))

        tampered_bytes = bytearray(create_mock_header())
        tampered_bytes[0x20] ^= 0xFF
        with self.assertRaises(CorruptedDataError):
            WiaHeader.read(BytesIO(tampered_bytes))

class TestWiaDisc(unittest.TestCase):
    def test_reads_a_zstd_disc(self):
        """Fields land at the right offsets, and the level is read as signed"""
        raw = bytearray(DISC_SIZE)
        raw[0x00:0x04] = struct.pack(">I", WiaDiscType.WII)
        raw[0x04:0x08] = struct.pack(">I", WiaCompression.ZSTD)
        raw[0x08:0x0C] = struct.pack(">i", -3)
        raw[0x0C:0x10] = struct.pack(">I", 0x20000)
        raw[0x90:0x94] = struct.pack(">I", 2)

        disc = WiaDisc.read(BytesIO(bytes(raw)))

        self.assertEqual(disc.disc_type, WiaDiscType.WII)
        self.assertEqual(disc.compression, WiaCompression.ZSTD)
        self.assertEqual(disc.compression_level, -3)
        self.assertEqual(disc.chunk_size, 0x20000)
        self.assertEqual(disc.partition_count, 2)
        self.assertEqual(disc.partition_chunk_size, 0x1F000)

if __name__ == '__main__':
    unittest.main()