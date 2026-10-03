import tempfile
import unittest
from pathlib import Path

from wiithon import IsoOutput, convert
from wiithon.exceptions import InvalidFormatError


class TestConvert(unittest.TestCase):
    def test_refuses_a_source_it_cannot_read(self):
        """An ISO in, an ISO out, would just be a copy"""
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "not-an-image.bin"
            source.write_bytes(b"\x00" * 0x100)

            with self.assertRaises(InvalidFormatError):
                convert(str(source), str(Path(directory) / "out.iso"), IsoOutput())

    def test_refuses_an_output_it_cannot_write(self):
        with self.assertRaises(NotImplementedError):
            convert("in.rvz", "out.bin", object())