import struct
import unittest
from io import BytesIO

from structs.WiiPartitionHeader import WiiPartitionHeader
from structs.Ticket import Ticket


class TestWiiPartitionHeader(unittest.TestCase):
    """Unit tests for WiiPartitionHeader."""

    def _build_raw_ticket(self) -> bytes:
        """Build a minimal valid raw ticket for embedding in the header.

        Returns:
            Raw bytes of a valid ticket.
        """
        buf = BytesIO()
        buf.write(struct.pack('>I', 0x00010001))     # sig_type RSA_2048
        buf.write(b'\xAA' * 0x100)                   # sig
        buf.write(b'\x00' * 60)                      # padding
        buf.write(b'\x00' * 0x40)                    # sig_issuer
        buf.write(b'\x00' * 0x3C)                    # ecdh
        buf.write(b'\x00' * 3)                       # padding
        buf.write(b'\xCC' * 16)                      # encrypted_key
        buf.write(b'\x00' * 1)                       # padding
        buf.write(b'\x00' * 8)                       # ticket_id
        buf.write(b'\x00' * 4)                       # console_id
        buf.write(b'\x00' * 8)                       # title_id
        buf.write(struct.pack('>H', 0))              # unk
        buf.write(struct.pack('>H', 0))              # ticket_version
        buf.write(struct.pack('>I', 0))              # permitted_titles_mask
        buf.write(struct.pack('>I', 0))              # permit_mask
        buf.write(struct.pack('>B', 0))              # title_export_allowed
        buf.write(struct.pack('>B', 0))              # common_key_idx
        buf.write(b'\x00' * 48)                      # padding
        buf.write(b'\x00' * 0x40)                    # content_access_permissions
        buf.write(struct.pack('>H', 0))              # unk2
        for _ in range(8):
            buf.write(struct.pack('>II', 0, 0))      # time_limits
        return buf.getvalue()

    def _build_raw_header(self) -> bytes:
        """Build raw binary data for a WiiPartitionHeader.

        Returns:
            Raw bytes representing a complete partition header.
        """
        buf = BytesIO()

        # Ticket
        buf.write(self._build_raw_ticket())

        # Partition metadata (all shifted offsets stored as value >> 2)
        buf.write(struct.pack('>I', 0x1000))         # tmd_size
        buf.write(struct.pack('>I', 0x2A4 >> 2))     # tmd_offset (shifted)
        buf.write(struct.pack('>I', 0xA00))           # cert_chain_size
        buf.write(struct.pack('>I', 0x10000 >> 2))   # cert_chain_offset (shifted)
        buf.write(struct.pack('>I', 0x8000 >> 2))    # global_hash_table_offset (shifted)
        buf.write(struct.pack('>I', 0x20000 >> 2))   # data_offset (shifted)
        buf.write(struct.pack('>I', 0x100000 >> 2))  # data_size (shifted)

        return buf.getvalue()

    def test_read_fields(self) -> None:
        """Test that all fields are correctly parsed."""
        raw = self._build_raw_header()
        header = WiiPartitionHeader.read(BytesIO(raw))

        self.assertIsNotNone(header)
        self.assertIsNotNone(header.ticket)
        self.assertEqual(header.tmd_size, 0x1000)
        self.assertEqual(header.tmd_offset, 0x2A4)
        self.assertEqual(header.certificate_chain_size, 0xA00)
        self.assertEqual(header.certificate_chain_offset, 0x10000)
        self.assertEqual(header.global_hash_table_offset, 0x8000)
        self.assertEqual(header.data_offset, 0x20000)
        self.assertEqual(header.data_size, 0x100000)

    def test_shifted_offsets(self) -> None:
        """Test that shifted offsets are correctly multiplied by 4."""
        raw = self._build_raw_header()
        header = WiiPartitionHeader.read(BytesIO(raw))

        # All offsets should be multiples of 4
        self.assertEqual(header.tmd_offset % 4, 0)
        self.assertEqual(header.certificate_chain_offset % 4, 0)
        self.assertEqual(header.data_offset % 4, 0)

    def test_roundtrip(self) -> None:
        """Test that read -> write -> read produces identical results."""
        raw = self._build_raw_header()
        header1 = WiiPartitionHeader.read(BytesIO(raw))

        out = BytesIO()
        header1.write(out)

        out.seek(0)
        header2 = WiiPartitionHeader.read(out)

        self.assertEqual(header1.tmd_size, header2.tmd_size)
        self.assertEqual(header1.tmd_offset, header2.tmd_offset)
        self.assertEqual(header1.certificate_chain_size, header2.certificate_chain_size)
        self.assertEqual(header1.certificate_chain_offset, header2.certificate_chain_offset)
        self.assertEqual(header1.global_hash_table_offset, header2.global_hash_table_offset)
        self.assertEqual(header1.data_offset, header2.data_offset)
        self.assertEqual(header1.data_size, header2.data_size)
        self.assertEqual(header1.ticket.title_key, header2.ticket.title_key)


if __name__ == "__main__":
    unittest.main()