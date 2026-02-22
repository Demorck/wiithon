import struct
import unittest
from io import BytesIO

from file_system_table.FST import FST
from file_system_table.FSTNode import FSTFile, FSTDirectory


class TestFST(unittest.TestCase):
    """Unit tests for FST read/write."""

    def _build_raw_fst(self) -> bytes:
        """Build a raw binary FST for testing.

        Tree structure:
          root/
            Data/
              movie/
                intro.thp (offset=0x1000, size=0x5000)
              icon.png    (offset=0x6000, size=0x800)

        Flat layout:
          [0] root    (dir, length=5)
          [1] Data    (dir, length=5)
          [2] movie   (dir, length=4)
          [3] intro   (file)
          [4] icon    (file)
        """
        buf = BytesIO()

        # String table (built first to know offsets)
        # offset 0: "" (root, empty)
        # offset 1: "Data"
        # offset 6: "movie"
        # offset 12: "intro.thp"
        # offset 22: "icon.png"
        strings = b'\x00Data\x00movie\x00intro.thp\x00icon.png\x00'

        # Node table
        nodes = [
            (True, 0, 0, 5),         # [0] root: dir, name="", length=5
            (True, 1, 0, 5),         # [1] Data: dir, name="Data", length=5
            (True, 6, 0, 4),         # [2] movie: dir, name="movie", length=4
            (False, 12, 0x1000, 0x5000),  # [3] intro.thp: file
            (False, 22, 0x6000, 0x800),   # [4] icon.png: file
        ]

        for is_dir, name_off, data_off, length in nodes:
            buf.write(struct.pack('>B', 1 if is_dir else 0))
            buf.write(bytes([
                (name_off >> 16) & 0xFF,
                (name_off >> 8) & 0xFF,
                name_off & 0xFF,
            ]))
            buf.write(struct.pack('>II', data_off, length))

        buf.write(strings)
        return buf.getvalue()

    def test_read(self) -> None:
        """Test reading a raw FST into a tree."""
        raw = self._build_raw_fst()
        fst = FST.read(BytesIO(raw), offset=0)

        # Should have one top-level entry: Data
        self.assertEqual(len(fst.entries), 1)
        data = fst.entries[0]
        self.assertIsInstance(data, FSTDirectory)
        self.assertEqual(data.name, "Data")

        # Data has 2 children: movie/ and icon.png
        self.assertEqual(len(data.children), 2)

        movie = data.children[0]
        self.assertIsInstance(movie, FSTDirectory)
        self.assertEqual(movie.name, "movie")

        icon = data.children[1]
        self.assertIsInstance(icon, FSTFile)
        self.assertEqual(icon.name, "icon.png")
        self.assertEqual(icon.offset, 0x6000)

        # movie has 1 child: intro.thp
        intro = movie.children[0]
        self.assertIsInstance(intro, FSTFile)
        self.assertEqual(intro.name, "intro.thp")
        self.assertEqual(intro.offset, 0x1000)
        self.assertEqual(intro.length, 0x5000)

    def test_roundtrip(self) -> None:
        """Test read -> write -> read produces identical tree."""
        raw = self._build_raw_fst()
        fst1 = FST.read(BytesIO(raw), offset=0)

        out = BytesIO()
        fst1.write(out)

        out.seek(0)
        fst2 = FST.read(out, offset=0)

        # Compare trees
        self.assertEqual(len(fst1.entries), len(fst2.entries))
        self._compare_nodes(fst1.entries, fst2.entries)

    def test_write_empty(self) -> None:
        """Test writing an FST with no entries."""
        fst = FST()
        out = BytesIO()
        fst.write(out)

        out.seek(0)
        fst2 = FST.read(out, offset=0)
        self.assertEqual(len(fst2.entries), 0)

    def _compare_nodes(self, a: list, b: list) -> None:
        """Recursively compare two lists of FSTNodes."""
        self.assertEqual(len(a), len(b))
        for na, nb in zip(a, b):
            self.assertEqual(na.name, nb.name)
            self.assertEqual(type(na), type(nb))
            if isinstance(na, FSTFile):
                self.assertEqual(na.offset, nb.offset)
                self.assertEqual(na.length, nb.length)
            elif isinstance(na, FSTDirectory):
                self._compare_nodes(na.children, nb.children)


if __name__ == "__main__":
    unittest.main()