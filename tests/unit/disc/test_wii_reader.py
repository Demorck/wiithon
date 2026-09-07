import os
import shutil
import tempfile
import unittest
from pathlib import Path
from typing import BinaryIO
from unittest import mock

from wiithon.disc.reader import WiiIsoReader
from wiithon.exceptions import InvalidDiscError


class TestWiiIsoReader(unittest.TestCase):
    """Unit tests for WiiIsoReader."""

    @staticmethod
    def _close_all(handles: list[BinaryIO]) -> None:
        """Close every handle left open, so the temp directory can be removed.

        Args:
            handles: File objects captured during the test.
        """
        for handle in handles:
            if not handle.closed:
                handle.close()

    def test_closes_file_when_magic_word_is_invalid(self) -> None:
        """The file descriptor must be released when __init__ fails."""
        tmp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp_dir, ignore_errors=True)

        iso_path = os.path.join(tmp_dir, "not_an_iso.iso")
        with open(iso_path, "wb") as stream:
            stream.write(b'\x00' * 0x50000)

        opened: list[BinaryIO] = []
        self.addCleanup(self._close_all, opened)

        real_open = Path.open

        def tracking_open(self_obj, *args, **kwargs) -> BinaryIO:
            handle = real_open(self_obj, *args, **kwargs)
            opened.append(handle)
            return handle

        with mock.patch.object(Path, "open", tracking_open), self.assertRaises(InvalidDiscError):
            WiiIsoReader(iso_path)

        self.assertTrue(opened, "no file was opened")
        self.assertTrue(all(h.closed for h in opened), "a file descriptor was not released")


if __name__ == "__main__":
    unittest.main()