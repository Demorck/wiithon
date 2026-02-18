import struct
import unittest
from io import BytesIO

from structs.TMDContent import TMDContent

class TestTMDContent(unittest.TestCase):
    """Unit tests for TMDContent."""

    def _build_raw_content(self, content_id: int = 0x00000001,
                           index: int = 0,
                           content_type: int = 0x0001,
                           size: int = 0x1000,
                           hash_byte: int = 0xAA) -> bytes:
        """Build raw binary data for a single TMDContent.
        """
        buf = BytesIO()
        buf.write(struct.pack('>I', content_id))
        buf.write(struct.pack('>H', index))
        buf.write(struct.pack('>H', content_type))
        buf.write(struct.pack('>Q', size))
        buf.write(bytes([hash_byte] * 0x14))
        return buf.getvalue()

    def test_read_fields(self) -> None:
        """Test that all fields are correctly parsed."""
        raw = self._build_raw_content(
            content_id=42, index=3, content_type=0x4001, size=0xDEAD
        )
        content = TMDContent.read(BytesIO(raw))

        self.assertEqual(content.id, 42)
        self.assertEqual(content.index, 3)
        self.assertEqual(content.content_type, 0x4001)
        self.assertEqual(content.size, 0xDEAD)
        self.assertEqual(len(content.hash), 0x14)

    def test_roundtrip(self) -> None:
        """Test that read → write → read produces identical results."""
        raw = self._build_raw_content()
        content1 = TMDContent.read(BytesIO(raw))

        out = BytesIO()
        content1.write(out)

        out.seek(0)
        content2 = TMDContent.read(out)

        self.assertEqual(content1.id, content2.id)
        self.assertEqual(content1.index, content2.index)
        self.assertEqual(content1.content_type, content2.content_type)
        self.assertEqual(content1.size, content2.size)
        self.assertEqual(content1.hash, content2.hash)

    def test_binary_size(self) -> None:
        """Test that written output has the expected size (0x24 = 36 bytes)."""
        content = TMDContent()
        content.id = 1
        content.hash = b'\x00' * 0x14

        out = BytesIO()
        content.write(out)

        self.assertEqual(out.tell(), 0x24)

if __name__ == "__main__":
    unittest.main()