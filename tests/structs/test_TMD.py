import struct
import unittest
from io import BytesIO

from structs.TMD import TMD
from helpers.Enums import SignatureType

class TestTMD(unittest.TestCase):
    """Unit tests for TMD."""

    def _build_raw_tmd(self, num_contents: int = 2) -> bytes:
        """Build raw binary data for a TMD with N contents.
        """
        buf = BytesIO()

        # Signed blob header
        buf.write(struct.pack('>I', SignatureType.RSA_2048))  # sig_type
        buf.write(b'\xAA' * 0x100)                           # signature
        buf.write(b'\x00' * 0x3C)                            # padding 60

        # Main header
        buf.write(b'Root-CA00000001-CP00000004\x00'.ljust(0x40, b'\x00'))  # issuer
        buf.write(struct.pack('>B', 1))                      # version
        buf.write(struct.pack('>B', 0))                      # ca_crl_version
        buf.write(struct.pack('>B', 0))                      # signer_crl_version
        buf.write(struct.pack('>B', 0))                      # padding (is_virtual_wii)
        buf.write(struct.pack('>Q', 0x0000000100000035))      # system_version (IOS 53)
        buf.write(struct.pack('>Q', 0x00010000524D4745))      # title_id
        buf.write(struct.pack('>I', 0))                      # title_type
        buf.write(struct.pack('>H', 0))                      # group_id
        buf.write(b'\x00' * 0x38)                            # fakesign padding (56 bytes)
        buf.write(b'\x00' * 0x06)                            # padding 6
        buf.write(struct.pack('>I', 0))                      # access_flags
        buf.write(struct.pack('>H', 0x0100))                 # title_version
        buf.write(struct.pack('>H', num_contents))           # num_contents
        buf.write(struct.pack('>H', 0))                      # boot_idx
        buf.write(b'\x00' * 0x02)                            # padding 2

        # Contents
        for i in range(num_contents):
            buf.write(struct.pack('>I', i))                  # id
            buf.write(struct.pack('>H', i))                  # index
            buf.write(struct.pack('>H', 0x0001))             # type
            buf.write(struct.pack('>Q', 0x1000 * (i + 1)))   # size
            buf.write(bytes([0xBB + i] * 0x14))              # hash

        return buf.getvalue()

    def test_read_fields(self) -> None:
        """Test that header fields are correctly parsed."""
        raw = self._build_raw_tmd(num_contents=2)
        tmd = TMD.read(BytesIO(raw))

        self.assertEqual(tmd.signature_type, SignatureType.RSA_2048)
        self.assertEqual(len(tmd.signature), 0x100)
        self.assertEqual(tmd.version, 1)
        self.assertEqual(tmd.title_version, 0x0100)
        self.assertEqual(tmd.num_contents, 2)

    def test_contents_parsed(self) -> None:
        """Test that TMDContent entries are correctly parsed."""
        raw = self._build_raw_tmd(num_contents=3)
        tmd = TMD.read(BytesIO(raw))

        self.assertEqual(len(tmd.contents), 3)
        self.assertEqual(tmd.contents[0].id, 0)
        self.assertEqual(tmd.contents[1].id, 1)
        self.assertEqual(tmd.contents[2].id, 2)
        self.assertEqual(tmd.contents[0].size, 0x1000)
        self.assertEqual(tmd.contents[2].size, 0x3000)

    def test_roundtrip(self) -> None:
        """Test that read → write → read produces identical results."""
        raw = self._build_raw_tmd(num_contents=2)
        tmd1 = TMD.read(BytesIO(raw))

        out = BytesIO()
        tmd1.write(out)

        out.seek(0)
        tmd2 = TMD.read(out)

        self.assertEqual(tmd1.signature_type, tmd2.signature_type)
        self.assertEqual(tmd1.signature, tmd2.signature)
        self.assertEqual(tmd1.version, tmd2.version)
        self.assertEqual(tmd1.title_id, tmd2.title_id)
        self.assertEqual(tmd1.title_version, tmd2.title_version)
        self.assertEqual(len(tmd1.contents), len(tmd2.contents))
        for c1, c2 in zip(tmd1.contents, tmd2.contents):
            self.assertEqual(c1.id, c2.id)
            self.assertEqual(c1.size, c2.size)
            self.assertEqual(c1.hash, c2.hash)

    def test_num_contents_auto_calculated(self) -> None:
        """Test that write recalculates num_contents from the list."""
        raw = self._build_raw_tmd(num_contents=2)
        tmd = TMD.read(BytesIO(raw))

        # Remove one content manually
        tmd.contents.pop()
        self.assertEqual(tmd.num_contents, 2)  # Still old value

        # Write should update it
        out = BytesIO()
        tmd.write(out)

        out.seek(0)
        tmd2 = TMD.read(out)
        self.assertEqual(tmd2.num_contents, 1)  # Auto-updated!
        self.assertEqual(len(tmd2.contents), 1)


if __name__ == "__main__":
    unittest.main()