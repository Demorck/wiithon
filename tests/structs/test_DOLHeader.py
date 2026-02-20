import struct
import unittest
from io import BytesIO

from structs.DOLHeader import DOLHeader


class TestDOLHeader(unittest.TestCase):
    """Unit tests for DOLHeader."""

    def _build_raw_header(self) -> bytes:
        """Build raw binary data for a DOLHeader.
        """
        buf = BytesIO()

        # Text offsets (7 × u32) - only first 2 used
        text_offsets = [0x100, 0x2000, 0, 0, 0, 0, 0]
        buf.write(struct.pack('>7I', *text_offsets))

        # Data offsets (11 × u32) - only first 3 used
        data_offset = [0x5000, 0x6000, 0x7000, 0, 0, 0, 0, 0, 0, 0, 0]
        buf.write(struct.pack('>11I', *data_offset))

        # Text addresses (7 × u32)
        text_addrs = [0x80003100, 0x80005000, 0, 0, 0, 0, 0]
        buf.write(struct.pack('>7I', *text_addrs))

        # Data addresses (11 × u32)
        data_addrs = [0x80200000, 0x80300000, 0x80400000, 0, 0, 0, 0, 0, 0, 0, 0]
        buf.write(struct.pack('>11I', *data_addrs))

        # Text sizes (7 × u32)
        text_length = [0x1F00, 0x3000, 0, 0, 0, 0, 0]
        buf.write(struct.pack('>7I', *text_length))

        # Data sizes (11 × u32)
        data_length = [0x1000, 0x1000, 0x800, 0, 0, 0, 0, 0, 0, 0, 0]
        buf.write(struct.pack('>11I', *data_length))

        buf.write(struct.pack('>I', 0x80500000))  # bss_start
        buf.write(struct.pack('>I', 0x10000))     # bss_size
        buf.write(struct.pack('>I', 0x80003100))  # entry_point
        buf.write(b'\x00' * 0x1C)                 # padding 28 bytes

        return buf.getvalue()

    def test_read_fields(self) -> None:
        """Test that all fields are correctly parsed."""
        raw = self._build_raw_header()
        dol = DOLHeader.read(BytesIO(raw))

        self.assertEqual(dol.text_offset[0], 0x100)
        self.assertEqual(dol.text_offset[1], 0x2000)
        self.assertEqual(dol.text_offset[2], 0)
        self.assertEqual(dol.data_offset[0], 0x5000)
        self.assertEqual(dol.data_offset[2], 0x7000)
        self.assertEqual(dol.text_starts[0], 0x80003100)
        self.assertEqual(dol.data_length[2], 0x800)
        self.assertEqual(dol.bss_start, 0x80500000)
        self.assertEqual(dol.bss_size, 0x10000)
        self.assertEqual(dol.entry_point, 0x80003100)

    def test_array_lengths(self) -> None:
        """Test that all arrays have the correct length."""
        raw = self._build_raw_header()
        dol = DOLHeader.read(BytesIO(raw))

        self.assertEqual(len(dol.text_offset), 7)
        self.assertEqual(len(dol.data_offset), 11)
        self.assertEqual(len(dol.text_starts), 7)
        self.assertEqual(len(dol.data_starts), 11)
        self.assertEqual(len(dol.text_length), 7)
        self.assertEqual(len(dol.data_length), 11)

    def test_roundtrip(self) -> None:
        """Test that read ->  write -> read produces identical results."""
        raw = self._build_raw_header()
        dol1 = DOLHeader.read(BytesIO(raw))

        out = BytesIO()
        dol1.write(out)

        out.seek(0)
        dol2 = DOLHeader.read(out)

        self.assertEqual(dol1.text_offset, dol2.text_offset)
        self.assertEqual(dol1.data_offset, dol2.data_offset)
        self.assertEqual(dol1.text_starts, dol2.text_starts)
        self.assertEqual(dol1.data_starts, dol2.data_starts)
        self.assertEqual(dol1.text_length, dol2.text_length)
        self.assertEqual(dol1.data_length, dol2.data_length)
        self.assertEqual(dol1.bss_start, dol2.bss_start)
        self.assertEqual(dol1.bss_size, dol2.bss_size)
        self.assertEqual(dol1.entry_point, dol2.entry_point)

    def test_binary_size(self) -> None:
        """Test that the total size is 0x100 (256 bytes)."""
        raw = self._build_raw_header()
        self.assertEqual(len(raw), 0x100)

        dol = DOLHeader.read(BytesIO(raw))
        out = BytesIO()
        dol.write(out)
        self.assertEqual(out.tell(), 0x100)


if __name__ == "__main__":
    unittest.main()