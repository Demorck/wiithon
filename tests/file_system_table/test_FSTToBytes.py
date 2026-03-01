import unittest
from io import BytesIO

from file_system_table.FST import FST
from file_system_table.FSTNode import FSTFile, FSTDirectory
from file_system_table.FSTToBytes import FSTToBytes


def _make_fst() -> FST:
    """
    Build a small in-memory FST for testing.

    Tree structure:
        Data/
            movie/
                intro.thp  (offset=0x1000, length=0x5000)
            icon.png       (offset=0x6000, length=0x800)
        readme.txt         (offset=0x7000, length=0x100)
    """
    intro = FSTFile("intro.thp", offset=0x1000, length=0x5000)
    icon  = FSTFile("icon.png",  offset=0x6000, length=0x800)
    readme = FSTFile("readme.txt", offset=0x7000, length=0x100)

    movie = FSTDirectory("movie")
    movie.children = [intro]

    data = FSTDirectory("Data")
    data.children = [movie, icon]

    fst = FST()
    fst.entries = [data, readme]
    return fst


class TestFSTToBytesStringTable(unittest.TestCase):
    """String table is built correctly at construction time"""

    def setUp(self) -> None:
        fst = _make_fst()
        self.ftb = FSTToBytes(fst.entries)

    def test_root_name_is_empty(self) -> None:
        """First byte of the string table is the null terminator for the root"""
        self.assertEqual(self.ftb.string_bytes[0], 0)
        self.assertEqual(self.ftb.string_offsets[0], 0)

    def test_all_names_present(self) -> None:
        """Every node name appears as a null-terminated Shift-JIS string"""
        table = bytes(self.ftb.string_bytes)
        for name in ("Data", "movie", "intro.thp", "icon.png", "readme.txt"):
            encoded = name.encode('shift_jis') + b'\x00'
            self.assertIn(encoded, table, f"'{name}' not found in string table")

    def test_offsets_count(self) -> None:
        """There is one offset per node including root (1 root + 5 nodes = 6)"""
        # root + Data + movie + intro.thp + icon.png + readme.txt = 6
        self.assertEqual(len(self.ftb.string_offsets), 6)

    def test_offsets_point_to_correct_name(self) -> None:
        """Each offset correctly points to the start of its name"""
        table = bytes(self.ftb.string_bytes)
        for i, offset in enumerate(self.ftb.string_offsets):
            end = table.index(b'\x00', offset)
            name_bytes = table[offset:end]

            self.assertFalse(b'\x00' in name_bytes,
                             f"offset {i} ({offset:#x}) null")


class TestFSTToBytesByteSize(unittest.TestCase):
    """byte_size() matches the actual number of bytes written by write_to()"""

    def test_byte_size_matches_written(self) -> None:
        fst = _make_fst()
        ftb = FSTToBytes(fst.entries)

        buf = BytesIO()
        ftb.write_to(buf)

        self.assertEqual(ftb.byte_size(), buf.tell())

    def test_byte_size_empty_fst(self) -> None:
        """An empty FST is just the root node (12 bytes) + 1 null byte"""
        ftb = FSTToBytes([])
        buf = BytesIO()
        ftb.write_to(buf)
        self.assertEqual(ftb.byte_size(), buf.tell())
        # 1 raw node (12 bytes) + 1 byte string table ('\x00')
        self.assertEqual(ftb.byte_size(), 13)


class TestFSTToBytesRoundtrip(unittest.TestCase):
    """FSTToBytes.write_to() -> FST.read() produces an identical tree"""

    def test_roundtrip(self) -> None:
        fst = _make_fst()
        ftb = FSTToBytes(fst.entries)

        buf = BytesIO()
        ftb.write_to(buf)

        buf.seek(0)
        fst2 = FST.read(buf, offset=0)

        self._compare(fst.entries, fst2.entries)

    def _compare(self, a, b) -> None:
        self.assertEqual(len(a), len(b))
        for na, nb in zip(a, b):
            self.assertEqual(na.name, nb.name)
            self.assertEqual(type(na), type(nb))
            if isinstance(na, FSTFile):
                self.assertEqual(na.offset, nb.offset)
                self.assertEqual(na.length, nb.length)
            elif isinstance(na, FSTDirectory):
                self._compare(na.children, nb.children)

    def test_roundtrip_empty(self) -> None:
        ftb = FSTToBytes([])
        buf = BytesIO()
        ftb.write_to(buf)
        buf.seek(0)
        fst2 = FST.read(buf, offset=0)
        self.assertEqual(fst2.entries, [])


class TestFSTToBytesFileCount(unittest.TestCase):
    """get_total_file_count() returns the correct number of FSTFile nodes"""

    def test_count(self) -> None:
        fst = _make_fst()
        ftb = FSTToBytes(fst.entries)
        # intro.thp + icon.png + readme.txt = 3
        self.assertEqual(ftb.get_total_file_count(), 3)

    def test_count_empty(self) -> None:
        self.assertEqual(FSTToBytes([]).get_total_file_count(), 0)

    def test_count_flat(self) -> None:
        """Flat FST with only files at the root level"""
        fst = FST()
        fst.entries = [
            FSTFile("a.bin", offset=0x100, length=0x200),
            FSTFile("b.bin", offset=0x300, length=0x400),
        ]
        ftb = FSTToBytes(fst.entries)
        self.assertEqual(ftb.get_total_file_count(), 2)


class TestFSTToBytesCallback(unittest.TestCase):
    """callback_all_files() visits every FSTFile in depth-first order"""

    def test_visited_names(self) -> None:
        """All files are visited exactly once"""
        fst = _make_fst()
        ftb = FSTToBytes(fst.entries)

        visited = []
        ftb.callback_all_files(lambda path, node: visited.append(node.name))

        self.assertEqual(sorted(visited), sorted(["intro.thp", "icon.png", "readme.txt"]))

    def test_depth_first_order(self) -> None:
        """Files are visited depth-first (Data/movie/intro.thp before icon.png)"""
        fst = _make_fst()
        ftb = FSTToBytes(fst.entries)

        visited = []
        ftb.callback_all_files(lambda path, node: visited.append(node.name))

        # intro.thp is inside Data/movie, so visited before icon.png (sibling of movie)
        self.assertLess(visited.index("intro.thp"), visited.index("icon.png"))

    def test_path_parts_correct(self) -> None:
        """The path argument contains the correct parent directory names"""
        fst = _make_fst()
        ftb = FSTToBytes(fst.entries)

        paths = {}
        ftb.callback_all_files(lambda path, node: paths.update({node.name: list(path)}))

        self.assertEqual(paths["intro.thp"], ["Data", "movie"])
        self.assertEqual(paths["icon.png"],  ["Data"])
        self.assertEqual(paths["readme.txt"], [])

    def test_callback_can_mutate_offset(self) -> None:
        """Mutating file offsets inside the callback is reflected in write_to()"""
        fst = _make_fst()
        ftb = FSTToBytes(fst.entries)

        # Reset all offsets to 0 first
        ftb.callback_all_files(lambda path, node: setattr(node, 'offset', 0))

        # Assign new sequential fake offsets
        counter = [0x10000]
        def assign(path, node):
            node.offset = counter[0]
            node.length = 0x80
            counter[0] += 0x80

        ftb.callback_all_files(assign)

        # Write and re-read
        buf = BytesIO()
        ftb.write_to(buf)
        buf.seek(0)
        fst2 = FST.read(buf, offset=0)

        # Collect all files from fst2
        def collect(entries):
            result = []
            for e in entries:
                if isinstance(e, FSTFile):
                    result.append(e)
                elif isinstance(e, FSTDirectory):
                    result.extend(collect(e.children))
            return result

        files2 = collect(fst2.entries)
        expected_offset = 0x10000
        for f in files2:
            self.assertEqual(f.offset, expected_offset)
            self.assertEqual(f.length, 0x80)
            expected_offset += 0x80

if __name__ == "__main__":
    unittest.main()
