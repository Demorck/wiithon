import struct
import unittest
from io import BytesIO

from structs.WiiPartitionEntry import WiiPartitionEntry, read_parts


class TestReadParts(unittest.TestCase):
    """Unit tests for WiiPartTableEntry and read_parts."""

    def _build_fake_iso(self, partitions: list[tuple[int, int]]) -> BytesIO:
        """Build a fake ISO with a partition table at 0x40000."""
        # Create a buffer large enough
        buf = BytesIO(b'\x00' * 0x50000)

        # Write the first group header at 0x40000
        buf.seek(0x40000)
        buf.write(struct.pack('>I', len(partitions)))
        buf.write(struct.pack('>I', 0x40020 >> 2))

        for _ in range(3):
            buf.write(struct.pack('>II', 0, 0))

        # Write entries at 0x40020
        buf.seek(0x40020)
        for offset, part_type in partitions:
            buf.write(struct.pack('>I', offset >> 2))
            buf.write(struct.pack('>I', part_type))

        buf.seek(0)
        return buf

    def test_read_single_partition(self) -> None:
        """Test reading a disc with one DATA partition."""
        iso = self._build_fake_iso([(0xF800000, 0)])
        entries = read_parts(iso)

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].offset, 0xF800000)
        self.assertEqual(entries[0].part_type, 0)  # DATA

    def test_read_multiple_partitions(self) -> None:
        """Test reading a disc with DATA + UPDATE partitions."""
        iso = self._build_fake_iso([
            (0x50000, 1),
            (0xF800000, 0),
        ])
        entries = read_parts(iso)

        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0].offset, 0x50000)
        self.assertEqual(entries[0].part_type, 1)
        self.assertEqual(entries[1].offset, 0xF800000)
        self.assertEqual(entries[1].part_type, 0)

    def test_read_no_partitions(self) -> None:
        """Test reading an empty partition table."""
        iso = self._build_fake_iso([])
        entries = read_parts(iso)

        self.assertEqual(len(entries), 0)

    def test_entry_read(self) -> None:
        """Test reading a single WiiPartTableEntry."""
        buf = BytesIO()
        buf.write(struct.pack('>I', 0xF800000 >> 2))
        buf.write(struct.pack('>I', 0))
        buf.seek(0)

        entry = WiiPartitionEntry.read(buf)

        self.assertEqual(entry.offset, 0xF800000)
        self.assertEqual(entry.part_type, 0)

    def test_offsets_are_shifted(self) -> None:
        """Test that offsets are correctly multiplied by 4."""
        iso = self._build_fake_iso([(0xF800000, 0)])
        entries = read_parts(iso)

        self.assertEqual(entries[0].offset % 4, 0)
        self.assertGreater(entries[0].offset, 0)


if __name__ == "__main__":
    unittest.main()