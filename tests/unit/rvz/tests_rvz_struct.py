import struct
import unittest
from io import BytesIO

from unit.rvz._common import DATA_KEY, FIRST_SEGMENT, FLAG, PARTITION

from wiithon.crypto.layout import BLOCK_SIZE
from wiithon.rvz.structs.group import RvzGroup, WiaGroup
from wiithon.rvz.structs.partition import WiaPartition
from wiithon.rvz.structs.partition_data import WiaPartitionData
from wiithon.rvz.structs.raw_data import WiaRawData


class TestPartitionTable(unittest.TestCase):
    """The tables that say which part of the disc lives in which group"""

    def test_segment_locates_its_first_block(self):
        segment = WiaPartitionData.read(BytesIO(FIRST_SEGMENT))
        self.assertEqual(segment.first_block, 7940)
        self.assertEqual(segment.block_count, 256)
        self.assertEqual(segment.group_index, 127)
        self.assertEqual(segment.group_count, 4)
        self.assertEqual(segment.offset, 0xF820000)

    def test_partition_carries_its_key_then_its_segments(self):
        """Segments tile the partition end to end, which is what makes the group indices line up"""
        partition = WiaPartition.read(BytesIO(PARTITION))
        first, second = partition.segments

        self.assertEqual(partition.title_key, DATA_KEY)
        self.assertEqual(first.offset, 0xF820000)
        self.assertEqual(second.offset, 0x10020000)
        self.assertEqual(second.group_index, 131)
        self.assertEqual(first.offset + first.block_count * BLOCK_SIZE, second.offset)

    def test_raw_entry_is_widened_to_the_block(self):
        """The header may point in the middle of a block, so the entry grows backwards without moving its end"""
        entry = WiaRawData.read(BytesIO(struct.pack(">QQII", 0x80, 0x4FF80, 0, 1)))
        self.assertEqual(entry.offset, 0)
        self.assertEqual(entry.size, 0x50000)
        self.assertEqual(entry.offset + entry.size, 0x80 + 0x4FF80)

    def test_aligned_raw_entry_is_left_alone(self):
        entry = WiaRawData.read(BytesIO(struct.pack(">QQII", 0xF800000, 0x20000, 126, 1)))
        self.assertEqual(entry.offset, 0xF800000)
        self.assertEqual(entry.size, 0x20000)
        self.assertEqual(entry.group_index, 126)
        self.assertEqual(entry.group_count, 1)

    def test_reader_stops_at_the_end_of_the_structure(self):
        """Tables are stored back to back, so one entry must never eat into the next"""
        for structure, raw in (
            (WiaPartitionData, FIRST_SEGMENT),
            (WiaPartition, PARTITION),
            (WiaRawData, struct.pack(">QQII", 0, 0, 0, 0))
        ):
            stream = BytesIO(raw + FLAG)
            structure.read(stream)
            self.assertEqual(stream.read(4), FLAG)


class TestGroupEntries(unittest.TestCase):
    """Where a chunk of data sits in the file and how it was stored"""

    def test_wia_offset_is_stored_shifted(self):
        """Offsets are kept as a quarter of the real value so a 32 bit field can reach a whole image"""
        group = WiaGroup.read(BytesIO(struct.pack(">II", 0x2000, 0x50000)))
        self.assertEqual(group.offset, 0x8000)
        self.assertEqual(group.size, 0x50000)

    def test_wia_size_uses_the_whole_word(self):
        """WIA decides compression once in the header, so no bit is stolen from the size"""
        group = WiaGroup.read(BytesIO(struct.pack(">II", 0, 0x80000200)))
        self.assertEqual(group.size, 0x80000200)
        self.assertTrue(group.compressed)
        self.assertFalse(group.is_packed)
        self.assertFalse(group.is_zero)

    def test_rvz_reads_compression_from_the_high_bit(self):
        """RVZ steals the top bit of the size to mark a chunk that went through the packer"""
        packed = RvzGroup.read(BytesIO(struct.pack(">III", 0x40, 0x80000200, 0x1F0000)))
        self.assertEqual(packed.offset, 0x100)
        self.assertEqual(packed.size, 0x200)
        self.assertEqual(packed.packed_size, 0x1F0000)
        self.assertTrue(packed.compressed)
        self.assertTrue(packed.is_packed)

        stored = RvzGroup.read(BytesIO(struct.pack(">III", 0, 0x200, 0)))
        self.assertFalse(stored.compressed)
        self.assertFalse(stored.is_packed)

    def test_empty_group_is_a_hole_in_the_image(self):
        """Only the size bits decide, the compression flag says nothing about the content"""
        self.assertTrue(WiaGroup.read(BytesIO(struct.pack(">II", 0, 0))).is_zero)

        flagged = RvzGroup.read(BytesIO(struct.pack(">III", 0, 0x80000000, 0)))
        self.assertTrue(flagged.is_zero)
        self.assertTrue(flagged.compressed)

    def test_reader_stops_at_the_end_of_the_entry(self):
        """Group entries form a dense array, a wrong size would shift every following group"""
        for structure, raw in (
            (WiaGroup, struct.pack(">II", 1, 2)),
            (RvzGroup, struct.pack(">III", 1, 2, 3))
        ):
            stream = BytesIO(raw + FLAG)
            structure.read(stream)
            self.assertEqual(stream.read(4), FLAG)

    def test_block_aligned_entry_is_untouched(self):
        """0x50000 is block aligned but not group aligned, which separates the two"""
        entry = WiaRawData.read(BytesIO(struct.pack(">QQII", 0x50000, 0x20000, 1, 1)))

        self.assertEqual(entry.offset, 0x50000)
        self.assertEqual(entry.size, 0x20000)


if __name__ == "__main__":
    unittest.main()