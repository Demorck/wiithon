import tempfile
import unittest
from pathlib import Path

from tests.iso._common import (
    ISO_PATH,
    ISO_SIZE,
    RVZ_PATH,
    compare_range,
    needs_iso,
    needs_rvz,
)

from wiithon import IsoOutput, WiaReader, convert
from wiithon.crypto.layout import BLOCK_SIZE
from wiithon.exceptions import InvalidFormatError


@needs_rvz
@needs_iso
class TestConvert(unittest.TestCase):
    def test_convert_rebuilds_the_iso(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        target = Path(directory.name) / "converted.iso"

        convert(str(RVZ_PATH), str(target), IsoOutput())
        self.assertEqual(target.stat().st_size, ISO_SIZE)

        reader = WiaReader(str(RVZ_PATH))
        self.addCleanup(reader.close)

        with target.open("rb") as left, ISO_PATH.open("rb") as right:
            for partition in reader.partitions:
                for segment in partition.segments:
                    with self.subTest(segment=hex(segment.offset)):
                        compare_range(
                            left, right, segment.offset, segment.block_count * BLOCK_SIZE
                        )


class TestConvertRefusals(unittest.TestCase):
    def test_refuses_a_source_it_cannot_read(self):
        """An ISO in and an ISO out would just be a copy"""
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "not-an-image.bin"
            source.write_bytes(bytes(0x100))

            with self.assertRaises(InvalidFormatError):
                convert(str(source), str(Path(directory) / "out.iso"), IsoOutput())

    def test_refuses_an_output_it_cannot_write(self):
        with self.assertRaises(NotImplementedError):
            convert("in.rvz", "out.bin", object())

if __name__ == "__main__":
    unittest.main()