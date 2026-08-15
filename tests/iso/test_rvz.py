import unittest
from pathlib import Path

from wiithon.crypto.layout import BLOCK_DATA_SIZE, BLOCK_SIZE, GROUP_SIZE
from wiithon.rvz.enums import WiaCompression, WiaDiscType
from wiithon.rvz.reader import WiaReader
from wiithon.rvz.structs.group import WiaGroup

MOCK_DIR = Path(__file__).parent.parent / "mock_iso"
WIA_PATH = MOCK_DIR / "test.wia"
RVZ_PATH = MOCK_DIR / "test.rvz"

GAME_ID = b"FEUR69"
ISO_SIZE = 4_699_979_776


EXCEPTION_SIZE = 22

needs_wia = unittest.skipUnless(WIA_PATH.is_file(), "WIA not found")
needs_rvz = unittest.skipUnless(RVZ_PATH.is_file(), "RVZ not found")
needs_both = unittest.skipUnless(WIA_PATH.is_file() and RVZ_PATH.is_file(), "WIA or RVZ not found")


class TestMockImages(unittest.TestCase):
    """
    Two chunk size for the Elven-Kings under the sky
    Two writer for the Dwarf-lords in their halls of stone,
    ...
    One Disc to rule them all, one Disc to find them,
    One Disc to bring them all, and in the darkness bind them
    """

    def open_image(self, path: Path) -> WiaReader:
        reader = WiaReader(str(path))
        self.addCleanup(reader.close)
        return reader

    @needs_wia
    def test_wia_header_names_the_disc(self):
        """The image announces the disc it came from and its own size"""
        wia = self.open_image(WIA_PATH)
        self.assertFalse(wia.header.is_rvz)
        self.assertEqual(wia.header.iso_file_size, ISO_SIZE)
        self.assertEqual(wia.header.wia_file_size, WIA_PATH.stat().st_size)
        self.assertEqual(wia.disc.disc_type, WiaDiscType.WII)
        self.assertEqual(wia.disc.disc_head[:6], GAME_ID)

    @needs_wia
    def test_raw_areas_are_snapped_to_blocks(self):
        """Entries are widened to whole blocks but nothing forces them onto a group boundary"""
        first, last = self.open_image(WIA_PATH).raw_data[0], self.open_image(WIA_PATH).raw_data[-1]

        self.assertEqual(first.offset, 0)
        self.assertEqual(first.size, 0xF800000)
        self.assertEqual(last.offset % BLOCK_SIZE, 0)
        self.assertNotEqual(last.offset % GROUP_SIZE, 0)
        self.assertEqual(last.offset + last.size, ISO_SIZE)

    @needs_wia
    def test_descriptors_tile_the_whole_disc(self):
        """Raw areas and partition segments cover the image, no gap and no overlap"""
        wia = self.open_image(WIA_PATH)
        spans = [(entry.offset, entry.offset + entry.size) for entry in wia.raw_data]
        for partition in wia.partitions:
            spans += [
                (segment.offset, segment.offset + segment.block_count * BLOCK_SIZE)
                for segment in partition.segments
            ]

        spans.sort()
        self.assertEqual(spans[0][0], 0)
        self.assertEqual(spans[-1][1], ISO_SIZE)
        for (_, end), (start, _) in zip(spans, spans[1:], strict=False):
            self.assertEqual(end, start)

    @needs_wia
    def test_wia_never_yields_rvz_groups(self):
        """A WIA magic must not produce twelve byte group structures"""
        wia = self.open_image(WIA_PATH)
        self.assertEqual(len(wia.groups), wia.disc.group_count)
        for index, group in enumerate(wia.groups):
            with self.subTest(group=index):
                self.assertIs(type(group), WiaGroup)

    @needs_wia
    def test_raw_groups_hold_one_chunk_each(self):
        """Every group of a raw area holds one chunk, the last one holds the remainder"""
        wia = self.open_image(WIA_PATH)
        chunk = wia.disc.chunk_size

        for entry in wia.raw_data:
            for i in range(entry.group_count):
                index = entry.group_index + i
                if wia.groups[index].is_zero:
                    continue
                with self.subTest(group=index):
                    self.assertEqual(len(wia.read_group(index)), min(chunk, entry.size - i * chunk))

    @needs_wia
    def test_partition_groups_start_with_their_exceptions(self):
        """A partition group is a count, its exceptions, padding to four, then the payload"""
        wia = self.open_image(WIA_PATH)
        blocks_per_group = wia.disc.chunk_size // BLOCK_SIZE
        seen_exceptions = False

        for partition in wia.partitions:
            for segment in partition.segments:
                for i in range(segment.group_count):
                    index = segment.group_index + i
                    data = wia.read_group(index)
                    if not data:
                        continue

                    count = int.from_bytes(data[:2])
                    seen_exceptions |= count > 0
                    blocks = min(blocks_per_group, segment.block_count - i * blocks_per_group)

                    with self.subTest(group=index):
                        header = (2 + EXCEPTION_SIZE * count + 3) // 4 * 4
                        self.assertEqual(len(data), header + blocks * BLOCK_DATA_SIZE)

    @needs_rvz
    def test_rvz_header_announces_zstd(self):
        rvz = self.open_image(RVZ_PATH)
        self.assertTrue(rvz.header.is_rvz)
        self.assertEqual(rvz.header.iso_file_size, ISO_SIZE)
        self.assertEqual(rvz.header.wia_file_size, RVZ_PATH.stat().st_size)
        self.assertEqual(rvz.disc.compression, WiaCompression.ZSTD)
        self.assertEqual(rvz.disc.disc_head[:6], GAME_ID)

    @needs_rvz
    def test_rvz_gives_its_partitions_before_any_decoding(self):
        """Partition descriptors are never compressed so they work already"""
        rvz = self.open_image(RVZ_PATH)
        self.assertEqual(len(rvz.partitions), 1)
        self.assertEqual(len(rvz.partitions[0].segments), 2)

    @needs_both
    def test_both_files_describe_the_same_disc(self):
        """Same size, same header, same partitions cut at the same blocks"""
        wia, rvz = self.open_image(WIA_PATH), self.open_image(RVZ_PATH)

        self.assertEqual(wia.header.iso_file_size, rvz.header.iso_file_size)
        self.assertEqual(wia.disc.disc_head, rvz.disc.disc_head)
        self.assertEqual(len(wia.partitions), len(rvz.partitions))

        for index, (from_wia, from_rvz) in enumerate(zip(wia.partitions, rvz.partitions, strict=True)):
            with self.subTest(partition=index):
                self.assertEqual(from_wia.title_key, from_rvz.title_key)
                self.assertEqual(
                    [(segment.first_block, segment.block_count) for segment in from_wia.segments],
                    [(segment.first_block, segment.block_count) for segment in from_rvz.segments],
                )

    @needs_both
    def test_chunk_size_drives_the_group_count(self):
        """The two writers cut the disc differently, so the counts must not match"""
        wia, rvz = self.open_image(WIA_PATH), self.open_image(RVZ_PATH)
        self.assertNotEqual(wia.disc.chunk_size, rvz.disc.chunk_size)
        self.assertNotEqual(wia.disc.group_count, rvz.disc.group_count)


if __name__ == "__main__":
    unittest.main()