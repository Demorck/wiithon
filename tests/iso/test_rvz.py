import tempfile
import unittest
from pathlib import Path

from tests.iso._common import (
    COMPARE_BUFFER,
    EXCEPTION_SIZE,
    GAME_ID,
    ISO_PATH,
    ISO_SIZE,
    RVZ_PATH,
    WIA_PATH,
    needs_both,
    needs_iso,
    needs_rvz,
    needs_wia,
)

from wiithon.crypto.layout import BLOCK_DATA_SIZE, BLOCK_SIZE, GROUP_SIZE
from wiithon.rvz.enums import WiaCompression, WiaDiscType
from wiithon.rvz.reader import WiaReader
from wiithon.rvz.rebuilder import IsoRebuilder
from wiithon.rvz.structs.group import WiaGroup


class TestMockImages(unittest.TestCase):
    """
    Two chunk size for the Elven-Kings under the sky
    Two writer for the Dwarf-lords in their halls of stone,
    ...
    One Disc to rule them all, one Disc to find them,
    One Disc to bring them all, and in the darkness bind them
    """
    def rebuild(self, path: Path) -> Path:
        """
        Rebuild a whole image into a temporary file
        """

        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        target = Path(directory.name) / "rebuilt.iso"

        with target.open("w+b") as stream:
            IsoRebuilder(self.open_image(path)).write(stream)

        return target

    def rebuild_raw_data(self, path: Path) -> Path:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        target = Path(directory.name) / "rebuilt.iso"

        with target.open("w+b") as stream:
            IsoRebuilder(self.open_image(path)).write_raw_data(stream)

        return target

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
        for _, group in enumerate(wia.groups):
            self.assertIs(type(group), WiaGroup)

    @needs_wia
    def test_raw_groups_hold_one_chunk_each(self):
        """Every group of a raw area holds one chunk, the last one holds the remainder"""
        wia = self.open_image(WIA_PATH)
        chunk = wia.disc.chunk_size

        for entry in wia.raw_data:
            for i in range(entry.group_count):
                index = entry.first_group_index + i
                if wia.groups[index].is_zero:
                    continue
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

        for _, (from_wia, from_rvz) in enumerate(zip(wia.partitions, rvz.partitions, strict=True)):
            self.assertEqual(from_wia.title_key, from_rvz.title_key)
            self.assertEqual(
                [(segment.first_block, segment.block_count) for segment in from_wia.segments],
                [(segment.first_block, segment.block_count) for segment in from_rvz.segments],
            )

    @needs_both
    def test_chunk_size_drives_the_group_count(self):
        wia, rvz = self.open_image(WIA_PATH), self.open_image(RVZ_PATH)
        self.assertNotEqual(wia.disc.chunk_size, rvz.disc.chunk_size)
        self.assertNotEqual(wia.disc.group_count, rvz.disc.group_count)

    @needs_wia
    def test_partition_group_splits_into_exceptions_and_payload(self):
        """The first group of the data partition starts on the internal disc header"""
        wia = self.open_image(WIA_PATH)
        exceptions, payload = wia.read_partition_group(125)

        self.assertEqual(len(exceptions), 1)
        self.assertEqual(len(exceptions[0]), 2848)
        self.assertEqual(exceptions[0].exceptions[0].offset, 0x0354)
        self.assertEqual(exceptions[0].exceptions[-1].block, 63)
        self.assertEqual(len(payload), wia.disc.partition_chunk_size)
        self.assertEqual(payload[:6], GAME_ID)

    @needs_both
    def test_rebuilt_image_has_the_original_size(self):
        self.assertEqual(self.rebuild_raw_data(WIA_PATH).stat().st_size, ISO_SIZE)

    @needs_both
    def test_rebuilt_groups_match_the_iso(self):
        wia = self.open_image(WIA_PATH)
        chunk = wia.disc.chunk_size
        rebuilt = self.rebuild_raw_data(WIA_PATH)

        with rebuilt.open("rb") as left, ISO_PATH.open("rb") as right:
            for entry in wia.raw_data:
                for i in range(entry.group_count):
                    index = entry.first_group_index + i
                    if wia.groups[index].is_zero:
                        continue

                    offset = entry.offset + i * chunk
                    size = len(wia.read_group(index))
                    left.seek(offset)
                    right.seek(offset)

                    self.assertEqual(left.read(size), right.read(size))

    @needs_both
    def test_rebuilt_raw_areas_match_the_iso(self):
        wia = self.open_image(WIA_PATH)
        rebuilt = self.rebuild_raw_data(WIA_PATH)

        with rebuilt.open("rb") as left, ISO_PATH.open("rb") as right:
            for entry in wia.raw_data:
                left.seek(entry.offset)
                right.seek(entry.offset)
                remaining = entry.size

                while remaining:
                    count = min(COMPARE_BUFFER, remaining)
                    self.assertEqual(left.read(count), right.read(count))
                    remaining -= count


    @needs_wia
    @needs_iso
    def test_rebuilt_partitions_match_the_iso(self):
        wia = self.open_image(WIA_PATH)
        rebuilt = self.rebuild(WIA_PATH)

        with rebuilt.open("rb") as left, ISO_PATH.open("rb") as right:
            for partition in wia.partitions:
                for segment in partition.segments:
                    size = segment.block_count * BLOCK_SIZE
                    left.seek(segment.offset)
                    right.seek(segment.offset)

                    with self.subTest(segment=hex(segment.offset)):
                        self.assertEqual(left.read(size), right.read(size))

    @needs_wia
    @needs_iso
    def test_rebuilt_image_is_identical(self):
        rebuilt = self.rebuild(WIA_PATH)
        self.assertEqual(rebuilt.stat().st_size, ISO_SIZE)

        with rebuilt.open("rb") as left, ISO_PATH.open("rb") as right:
            while True:
                block = left.read(COMPARE_BUFFER)
                self.assertEqual(block, right.read(COMPARE_BUFFER))
                if not block:
                    break

if __name__ == "__main__":
    unittest.main()