import hashlib
import struct
import unittest
from io import BytesIO

from wiithon.exceptions import CorruptedDataError, InvalidFormatError
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


if __name__ == '__main__':
    unittest.main()