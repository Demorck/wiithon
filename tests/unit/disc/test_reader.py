import builtins
import os
import shutil
import tempfile
import unittest
from typing import BinaryIO
from unittest import mock

from wiithon.disc.WiiIsoReader import WiiIsoReader


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
        real_open = builtins.open

        def tracking_open(*args, **kwargs) -> BinaryIO:
            handle = real_open(*args, **kwargs)
            opened.append(handle)
            return handle

        with mock.patch.object(builtins, "open", tracking_open):
            with self.assertRaises(ValueError):
                WiiIsoReader(iso_path)

        self.assertTrue(opened, "no file was opened")
        self.assertTrue(all(h.closed for h in opened), "a file descriptor was not released")


if __name__ == "__main__":
    unittest.main()