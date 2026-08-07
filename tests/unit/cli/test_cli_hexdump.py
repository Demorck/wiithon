import unittest

from wiithon.cli._common import console
from wiithon.cli.iso import _print_hexdump


class TestHexdump(unittest.TestCase):

    def _dump(self, data: bytes, limit: int = 0) -> str:
        with console.capture() as capture:
            _print_hexdump(data, limit)
        return capture.get()

    def test_offsets_every_sixteen_bytes(self):
        output = self._dump(bytes(32))
        self.assertIn("00000000", output)
        self.assertIn("00000010", output)

    def test_hex_and_ascii_columns(self):
        output = self._dump(b"Exif")
        self.assertIn("45 78 69 66", output)
        self.assertIn("Exif", output)

    def test_non_printable_bytes_become_dots(self):
        self.assertIn("...", self._dump(b"\x00\x01\x02"))

    def test_square_brackets_survive_rich_markup(self):
        self.assertIn("[bold]", self._dump(b"[bold]"))

    def test_limit_truncates_and_reports_the_rest(self):
        output = self._dump(bytes(64), limit=16)
        self.assertIn("00000000", output)
        self.assertNotIn("00000010", output)
        self.assertIn("48 more byte", output)


if __name__ == "__main__":
    unittest.main()