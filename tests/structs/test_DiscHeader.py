import struct
import unittest
from io import BytesIO

from structs.DiscHeader import DiscHeader


class TestDiscHeader(unittest.TestCase):
    """Unit tests for DiscHeader."""

    def _build_raw_header(self) -> bytes:
        """Build raw binary data for a DiscHeader.

        Returns:
            Raw bytes representing a complete disc header.
        """
        buf = BytesIO()

        buf.write(b'RMGE01')                             # game_id (6 bytes)
        buf.write(struct.pack('>B', 0))                  # disc_num
        buf.write(struct.pack('>B', 0))                  # disc_version
        buf.write(struct.pack('>B', 1))                  # audio_streaming
        buf.write(struct.pack('>B', 0x20))               # audio_stream_buf_size
        buf.write(b'\x00' * 0x0E)                        # padding 14
        buf.write(struct.pack('>I', 0x5D1C9EA3))         # wii_magic_word
        buf.write(struct.pack('>I', 0))                  # gamecube_magic_word
        buf.write(b'Super Mario Galaxy\x00'.ljust(0x40, b'\x00'))  # game_title
        buf.write(struct.pack('>B', 0))                  # disable_hash_verification
        buf.write(struct.pack('>B', 0))                  # disable_disc_encryption
        buf.write(b'\x00' * 0x39E)                       # padding 926
        buf.write(struct.pack('>I', 0))                  # debug_mon_offset
        buf.write(struct.pack('>I', 0))                  # debug_load_address
        buf.write(b'\x00' * 0x18)                        # padding 24
        buf.write(struct.pack('>I', 0x12800 >> 2))       # DOL_offset (shifted)
        buf.write(struct.pack('>I', 0x40000 >> 2))       # FST_offset (shifted)
        buf.write(struct.pack('>I', 0x8000 >> 2))        # FST_size (shifted)
        buf.write(struct.pack('>I', 0x8000 >> 2))        # FST_max_size (shifted)
        buf.write(struct.pack('>I', 0x80000000))         # FST_memory_address
        buf.write(struct.pack('>I', 0))                  # user_position
        buf.write(struct.pack('>I', 0))                  # user_size
        buf.write(b'\x00' * 0x04)                        # padding 4

        return buf.getvalue()

    def test_read_fields(self) -> None:
        """Test that all fields are correctly parsed."""
        raw = self._build_raw_header()
        header = DiscHeader.read(BytesIO(raw))

        self.assertEqual(header.game_id, b'RMGE01')
        self.assertEqual(header.disc_num, 0)
        self.assertEqual(header.audio_streaming, 1)
        self.assertEqual(header.audio_stream_buf_size, 0x20)
        self.assertEqual(header.wii_magic_word, 0x5D1C9EA3)
        self.assertIn('Super Mario Galaxy', header.game_title)
        self.assertEqual(header.DOL_offset, 0x12800)
        self.assertEqual(header.FST_offset, 0x40000)
        self.assertEqual(header.FST_size, 0x8000)

    def test_shifted_offsets(self) -> None:
        """Test that shifted offsets are correctly multiplied by 4."""
        raw = self._build_raw_header()
        header = DiscHeader.read(BytesIO(raw))

        self.assertEqual(header.DOL_offset % 4, 0)
        self.assertEqual(header.FST_offset % 4, 0)
        self.assertEqual(header.FST_size % 4, 0)

    def test_roundtrip(self) -> None:
        """Test that read -> write -> read produces identical results."""
        raw = self._build_raw_header()
        header1 = DiscHeader.read(BytesIO(raw))

        out = BytesIO()
        header1.write(out)

        out.seek(0)
        header2 = DiscHeader.read(out)

        self.assertEqual(header1.game_id, header2.game_id)
        self.assertEqual(header1.disc_num, header2.disc_num)
        self.assertEqual(header1.disc_version, header2.disc_version)
        self.assertEqual(header1.audio_streaming, header2.audio_streaming)
        self.assertEqual(header1.wii_magic_word, header2.wii_magic_word)
        self.assertEqual(header1.game_title, header2.game_title)
        self.assertEqual(header1.DOL_offset, header2.DOL_offset)
        self.assertEqual(header1.FST_offset, header2.FST_offset)
        self.assertEqual(header1.FST_size, header2.FST_size)
        self.assertEqual(header1.FST_max_size, header2.FST_max_size)
        self.assertEqual(header1.user_position, header2.user_position)
        self.assertEqual(header1.user_size, header2.user_size)

    def test_binary_size(self) -> None:
        """Test that the total written size is correct (0x440 bytes)."""
        raw = self._build_raw_header()
        self.assertEqual(len(raw), 0x440)

        header = DiscHeader.read(BytesIO(raw))
        out = BytesIO()
        header.write(out)
        self.assertEqual(out.tell(), 0x440)


if __name__ == "__main__":
    unittest.main()