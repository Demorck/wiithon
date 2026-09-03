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

from wiithon.crypto.layout import BLOCK_DATA_SIZE, BLOCK_SIZE, GROUP_SIZE, BLOCK_PER_GROUP, BLOCK_HEADER_SIZE
from wiithon.rvz.enums import WiaCompression, WiaDiscType
from wiithon.rvz.layout import RVZ_GROUP_SIZE
from wiithon.rvz.reader import WiaReader
from wiithon.rvz.rebuilder import IsoRebuilder
from wiithon.rvz.structs.group import WiaGroup


class TestMockImages(unittest.TestCase):
    """
    Two chunk sizes for the Elven-Kings under the sky,
    Two writers for the Dwarf-lords in their halls of stone,
    ...
    One Disc to rule them all, one Disc to find them,
    One Disc to bring them all, and in the darkness bind them
    """

    def open_image(self, path: Path) -> WiaReader:
        reader = WiaReader(str(path))
        self.addCleanup(reader.close)
        return reader

    def rebuild(self, path: Path, raw_data_only: bool = False) -> Path:
        """Rebuild an image into a temporary file and hand back its path"""
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        target = Path(directory.name) / "rebuilt.iso"

        rebuilder = IsoRebuilder(self.open_image(path))
        with target.open("w+b") as stream:
            if raw_data_only:
                rebuilder.write_raw_data(stream)
            else:
                rebuilder.write(stream)

        return target

    def assert_same_range(self, rebuilt, reference, offset: int, size: int) -> None:
        """Compare one slice of the rebuilt image with the same slice of the reference ISO"""
        rebuilt.seek(offset)
        reference.seek(offset)

        while size:
            count = min(COMPARE_BUFFER, size)
            self.assertEqual(rebuilt.read(count), reference.read(count))
            size -= count

    def patched_hash_offsets(self, path: Path) -> set[int]:
        """
        Every hash the writer had to fix up, addressed from the start of the partition

        Group numbering follows the chunk size, so absolute offsets are the only common ground
        between two writers
        """
        reader = self.open_image(path)
        blocks_per_chunk = reader.disc.chunk_size // BLOCK_SIZE
        offsets = set()

        for partition in reader.partitions:
            for segment in partition.segments:
                for chunk in range(segment.group_count):
                    lists, _ = reader.read_partition_group(segment.group_index + chunk)
                    for sub_group, listing in enumerate(lists):
                        first_block = chunk * blocks_per_chunk + sub_group * BLOCK_PER_GROUP
                        for exception in listing.exceptions:
                            block = first_block + exception.block
                            offsets.add(block * BLOCK_HEADER_SIZE + exception.offset_in_block)

        return offsets

    @needs_wia
    def test_wia_header_names_the_disc(self):
        """The image announces the disc it came from and its own size"""
        wia = self.open_image(WIA_PATH)
        self.assertFalse(wia.header.is_rvz)
        self.assertEqual(wia.header.iso_file_size, ISO_SIZE)
        self.assertEqual(wia.header.wia_file_size, WIA_PATH.stat().st_size)
        self.assertEqual(wia.disc.disc_type, WiaDiscType.WII)
        self.assertEqual(wia.disc.disc_head[:6], GAME_ID)

    @needs_rvz
    def test_rvz_header_announces_zstd(self):
        rvz = self.open_image(RVZ_PATH)
        self.assertTrue(rvz.header.is_rvz)
        self.assertEqual(rvz.header.iso_file_size, ISO_SIZE)
        self.assertEqual(rvz.header.wia_file_size, RVZ_PATH.stat().st_size)
        self.assertEqual(rvz.disc.compression, WiaCompression.ZSTD)
        self.assertEqual(rvz.disc.disc_head[:6], GAME_ID)

    @needs_wia
    def test_raw_areas_are_snapped_to_blocks(self):
        """Entries are widened to whole blocks but nothing forces them onto a group boundary"""
        raw_data = self.open_image(WIA_PATH).raw_data
        first, last = raw_data[0], raw_data[-1]

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
        for group in wia.groups:
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
    def test_partition_group_is_exceptions_then_payload(self):
        """A partition group is a count, its exceptions, padding to four, then the decrypted blocks"""
        wia = self.open_image(WIA_PATH)

        # Group 125 starts on the internal disc header, and its hashes were all patched
        exceptions, payload = wia.read_partition_group(125)
        self.assertEqual(len(exceptions), 1)
        self.assertEqual(len(exceptions[0]), 2848)
        self.assertEqual(exceptions[0].exceptions[0].offset, 0x0354)
        self.assertEqual(exceptions[0].exceptions[-1].block, 63)
        self.assertEqual(len(payload), wia.disc.partition_chunk_size)
        self.assertEqual(payload[:6], GAME_ID)

        blocks_per_group = wia.disc.chunk_size // BLOCK_SIZE
        for partition in wia.partitions:
            for segment in partition.segments:
                for i in range(segment.group_count):
                    data = wia.read_group(segment.group_index + i)
                    if not data:
                        continue

                    count = int.from_bytes(data[:2])
                    blocks = min(blocks_per_group, segment.block_count - i * blocks_per_group)
                    header = (2 + EXCEPTION_SIZE * count + 3) // 4 * 4
                    self.assertEqual(len(data), header + blocks * BLOCK_DATA_SIZE)

    @needs_rvz
    def test_rvz_gives_its_partitions_before_any_decoding(self):
        """Partition descriptors are never compressed so they work already"""
        rvz = self.open_image(RVZ_PATH)
        self.assertEqual(len(rvz.partitions), 1)
        self.assertEqual(len(rvz.partitions[0].segments), 2)

    @needs_rvz
    def test_rvz_descriptors_survive_compression(self):
        """The tables come out whole, and they really were packed on the way in"""
        rvz = self.open_image(RVZ_PATH)

        self.assertEqual(len(rvz.raw_data), rvz.disc.raw_data_count)
        self.assertEqual(len(rvz.groups), rvz.disc.group_count)
        self.assertLess(rvz.disc.group_size, rvz.disc.group_count * RVZ_GROUP_SIZE)

    @needs_rvz
    def test_rvz_raw_group_expands_to_a_whole_chunk(self):
        rvz = self.open_image(RVZ_PATH)
        entry = rvz.raw_data[0]

        self.assertEqual(len(rvz.read_group(entry.first_group_index)), rvz.disc.chunk_size)

    @needs_rvz
    def test_a_chunk_may_opt_out_of_the_compression(self):
        """Incompressible data is stored plain, and the reader must not try to decode it"""
        rvz = self.open_image(RVZ_PATH)
        stored_plain = [group for group in rvz.groups if not group.is_zero and not group.compressed]

        self.assertTrue(stored_plain)
        for group in stored_plain:
            with self.subTest(offset=hex(group.offset)):
                self.assertTrue(rvz._is_stored_plain(group))

    @needs_both
    def test_both_files_describe_the_same_disc(self):
        """Same size, same header, same partitions cut at the same blocks"""
        wia, rvz = self.open_image(WIA_PATH), self.open_image(RVZ_PATH)

        self.assertEqual(wia.header.iso_file_size, rvz.header.iso_file_size)
        self.assertEqual(wia.disc.disc_head, rvz.disc.disc_head)
        self.assertEqual(len(wia.partitions), len(rvz.partitions))

        for from_wia, from_rvz in zip(wia.partitions, rvz.partitions, strict=True):
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

    @needs_both
    def test_both_images_carry_the_same_exceptions(self):
        """The patched hashes belong to the disc, not to the writer that dumped it"""
        self.assertEqual(self.patched_hash_offsets(WIA_PATH), self.patched_hash_offsets(RVZ_PATH))

    @needs_wia
    @needs_iso
    def test_raw_data_is_rebuilt_byte_for_byte(self):
        """Raw areas are copied straight through, holes included"""
        wia = self.open_image(WIA_PATH)
        rebuilt = self.rebuild(WIA_PATH, raw_data_only=True)
        self.assertEqual(rebuilt.stat().st_size, ISO_SIZE)

        with rebuilt.open("rb") as left, ISO_PATH.open("rb") as right:
            for entry in wia.raw_data:
                with self.subTest(area=hex(entry.offset)):
                    self.assert_same_range(left, right, entry.offset, entry.size)

    @needs_wia
    @needs_iso
    def test_partitions_are_rebuilt_byte_for_byte(self):
        """Re-encrypting and re-hashing a segment must land on the original bytes"""
        wia = self.open_image(WIA_PATH)
        rebuilt = self.rebuild(WIA_PATH)

        with rebuilt.open("rb") as left, ISO_PATH.open("rb") as right:
            for partition in wia.partitions:
                for segment in partition.segments:
                    with self.subTest(segment=hex(segment.offset)):
                        self.assert_same_range(left, right, segment.offset, segment.block_count * BLOCK_SIZE)

    @needs_wia
    @needs_iso
    def test_the_whole_image_is_rebuilt_byte_for_byte(self):
        """The end goal: what comes out is the disc that went in, padding and all"""
        rebuilt = self.rebuild(WIA_PATH)
        self.assertEqual(rebuilt.stat().st_size, ISO_SIZE)

        with rebuilt.open("rb") as left, ISO_PATH.open("rb") as right:
            self.assert_same_range(left, right, 0, ISO_SIZE)

if __name__ == '__main__':
    unittest.main()