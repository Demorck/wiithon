import tempfile
import unittest
from pathlib import Path

from tests.iso._common import (
    EXCEPTION_SIZE,
    GAME_ID,
    ISO_PATH,
    ISO_SIZE,
    WIA_PATH,
    compare_range,
    discover_images,
    needs_iso,
    needs_slow,
    needs_wia,
    patched_hash_offsets,
)

from wiithon.binary.align import align
from wiithon.crypto.layout import BLOCK_DATA_SIZE, BLOCK_SIZE, GROUP_SIZE
from wiithon.rvz.enums import WiaDiscType
from wiithon.rvz.reader import WiaReader
from wiithon.rvz.rebuilder import IsoRebuilder


class Shared:
    class ImageCases(unittest.TestCase):
        """
        Checks that must hold for any image, whoever wrote it and however it is cut

        One subclass is generated per file found next to the mock ISO, so dropping a
        new conversion in that folder is enough to have it covered.
        """

        path: Path
        reader: WiaReader
        rebuilt: Path

        @classmethod
        def setUpClass(cls) -> None:
            cls.reader = WiaReader(str(cls.path))
            cls.addClassCleanup(cls.reader.close)

            directory = tempfile.TemporaryDirectory()
            cls.addClassCleanup(directory.cleanup)
            cls.rebuilt = Path(directory.name) / "rebuilt.iso"

            try:
                with cls.rebuilt.open("w+b") as stream:
                    IsoRebuilder(cls.reader).write(stream)
            except NotImplementedError as unsupported:
                raise unittest.SkipTest(str(unsupported)) from unsupported

            directory = tempfile.TemporaryDirectory()
            cls.addClassCleanup(directory.cleanup)

            cls.rebuilt = Path(directory.name) / "rebuilt.iso"
            with cls.rebuilt.open("w+b") as stream:
                IsoRebuilder(cls.reader).write(stream)

        def test_header_names_the_disc(self):
            """Whatever the container, it points at the same disc"""
            self.assertEqual(self.reader.header.iso_file_size, ISO_SIZE)
            self.assertEqual(self.reader.header.wia_file_size, self.path.stat().st_size)
            self.assertEqual(self.reader.disc.disc_type, WiaDiscType.WII)
            self.assertEqual(self.reader.disc.disc_head[:6], GAME_ID)

        def test_descriptors_tile_the_whole_disc(self):
            """Raw areas and partition segments cover the image, no gap and no overlap"""
            spans = [(entry.offset, entry.offset + entry.size) for entry in self.reader.raw_data]
            for partition in self.reader.partitions:
                spans += [
                    (segment.offset, segment.offset + segment.block_count * BLOCK_SIZE)
                    for segment in partition.segments
                ]

            spans.sort()
            self.assertEqual(spans[0][0], 0)
            self.assertEqual(spans[-1][1], ISO_SIZE)
            for (_, end), (start, _) in zip(spans, spans[1:], strict=False):
                self.assertEqual(end, start)

        def test_raw_groups_hold_one_chunk_each(self):
            chunk = self.reader.disc.chunk_size
            for entry in self.reader.raw_data:
                for i in range(entry.group_count):
                    index = entry.first_group_index + i
                    if self.reader.groups[index].is_zero:
                        continue
                    with self.subTest(group=index):
                        self.assertEqual(
                            len(self.reader.read_raw_group(entry, i)),
                            min(chunk, entry.size - i * chunk),
                        )

        def test_partition_groups_are_exceptions_then_payload(self):
            blocks_per_chunk = self.reader.disc.chunk_size // BLOCK_SIZE
            expected_lists = max(1, self.reader.disc.chunk_size // GROUP_SIZE)

            for partition in self.reader.partitions:
                partition_first_block = partition.segments[0].first_block

                for segment in partition.segments:
                    for i in range(segment.group_count):
                        index = segment.group_index + i
                        group = self.reader.groups[index]
                        stored = self.reader.read_group(index)
                        if not stored:
                            continue

                        block = segment.first_block - partition_first_block + i * blocks_per_chunk
                        lists, payload = self.reader.read_partition_group(
                            index, block * BLOCK_DATA_SIZE
                        )

                        header = 2 * len(lists) + EXCEPTION_SIZE * sum(len(one) for one in lists)
                        if self.reader._is_stored_plain(group):
                            header = align(header, 4)

                        blocks = min(blocks_per_chunk, segment.block_count - i * blocks_per_chunk)

                        with self.subTest(group=index):
                            self.assertEqual(len(lists), expected_lists)
                            self.assertEqual(len(payload), blocks * BLOCK_DATA_SIZE)

                            if group.is_packed:
                                self.assertEqual(group.packed_size, len(stored) - header)
                            else:
                                self.assertEqual(len(stored), header + len(payload))

        @needs_wia
        def test_patched_hashes_match_the_reference(self):
            """Every writer must name the same hashes, once put back in the frame of the disc"""
            self.assertEqual(
                patched_hash_offsets(self.reader), patched_hash_offsets(WiaReader(str(WIA_PATH)))
            )

        @needs_iso
        def test_partitions_are_rebuilt_byte_for_byte(self):
            with self.rebuilt.open("rb") as left, ISO_PATH.open("rb") as right:
                for partition in self.reader.partitions:
                    for segment in partition.segments:
                        with self.subTest(segment=hex(segment.offset)):
                            compare_range(left, right, segment.offset, segment.block_count * BLOCK_SIZE)

        @needs_iso
        @needs_slow
        def test_the_whole_image_is_rebuilt_byte_for_byte(self):
            self.assertEqual(self.rebuilt.stat().st_size, ISO_SIZE)
            with self.rebuilt.open("rb") as left, ISO_PATH.open("rb") as right:
                compare_range(left, right, 0, ISO_SIZE)


for _image in discover_images():
    _name = "TestImage_" + _image.name.replace(".", "_").replace("-", "_")
    globals()[_name] = type(_name, (Shared.ImageCases,), {"path": _image})