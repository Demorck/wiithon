import os
import tempfile
import unittest

from wiithon.builder.DirectoryPartitionBuilder import (
    build_from_directory_tree,
    DirectoryPartitionBuilder,
)
from wiithon.file_system_table.FSTNode import FSTFile, FSTDirectory


#  build_from_directory_tree
class TestBuildFromDirectoryTree(unittest.TestCase):

    def _build(self, setup_fn) -> object:
        with tempfile.TemporaryDirectory() as d:
            setup_fn(d)
            return build_from_directory_tree(d)

    def test_empty_directory_gives_empty_fst(self):
        fst = self._build(lambda d: None)
        self.assertEqual(fst.entries, [])

    def test_single_file_at_root(self):
        def setup(d):
            open(os.path.join(d, "file.bin"), "wb").close()

        fst = self._build(setup)
        self.assertEqual(len(fst.entries), 1)
        self.assertIsInstance(fst.entries[0], FSTFile)
        self.assertEqual(fst.entries[0].name, "file.bin")

    def test_file_length_matches_size_on_disk(self):
        def setup(d):
            with open(os.path.join(d, "data.bin"), "wb") as f:
                f.write(b"x" * 256)

        fst = self._build(setup)
        self.assertEqual(fst.entries[0].length, 256)

    def test_file_initial_offset_is_zero(self):
        """L'offset est 0 à la construction — WiiDiscBuilder l'assignera plus tard."""
        def setup(d):
            open(os.path.join(d, "file.bin"), "wb").close()

        fst = self._build(setup)
        self.assertEqual(fst.entries[0].offset, 0)

    def test_subdirectory_becomes_fst_directory(self):
        def setup(d):
            os.mkdir(os.path.join(d, "subdir"))

        fst = self._build(setup)
        self.assertEqual(len(fst.entries), 1)
        self.assertIsInstance(fst.entries[0], FSTDirectory)
        self.assertEqual(fst.entries[0].name, "subdir")

    def test_nested_file_is_child_of_directory(self):
        def setup(d):
            sub = os.path.join(d, "ObjectData")
            os.mkdir(sub)
            with open(os.path.join(sub, "scene.arc"), "wb") as f:
                f.write(b"arc")

        fst = self._build(setup)
        obj_dir = fst.entries[0]
        self.assertIsInstance(obj_dir, FSTDirectory)
        self.assertEqual(len(obj_dir.children), 1)
        self.assertEqual(obj_dir.children[0].name, "scene.arc")

    def test_entries_sorted_case_insensitive(self):
        def setup(d):
            for name in ("Zebra.bin", "alpha.bin", "Middle.bin"):
                open(os.path.join(d, name), "wb").close()

        fst = self._build(setup)
        names = [e.name.lower() for e in fst.entries]
        self.assertEqual(names, sorted(names))

    def test_mixed_files_and_dirs_sorted_together(self):
        def setup(d):
            os.mkdir(os.path.join(d, "BDir"))
            open(os.path.join(d, "afile.bin"), "wb").close()
            open(os.path.join(d, "cfile.bin"), "wb").close()

        fst = self._build(setup)
        names = [e.name.lower() for e in fst.entries]
        self.assertEqual(names, sorted(names))


#  DirectoryPartitionBuilder.get_file_data
class TestDirectoryPartitionBuilderGetFileData(unittest.TestCase):
    """
    Contourne __init__ avec object.__new__ pour tester get_file_data
    sans devoir créer tous les fichiers binaires (tmd.bin, cert.bin, etc.).
    """

    def _make_builder(self, files_dir: str) -> DirectoryPartitionBuilder:
        builder = object.__new__(DirectoryPartitionBuilder)
        builder.files_dir = files_dir
        return builder

    def test_reads_file_at_root(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "root.bin"), "wb") as f:
                f.write(b"root_content")
            self.assertEqual(
                self._make_builder(d).get_file_data(["root.bin"]),
                b"root_content",
            )

    def test_reads_file_in_subdirectory(self):
        with tempfile.TemporaryDirectory() as d:
            sub = os.path.join(d, "ObjectData")
            os.mkdir(sub)
            with open(os.path.join(sub, "scene.arc"), "wb") as f:
                f.write(b"arc_bytes")
            self.assertEqual(
                self._make_builder(d).get_file_data(["ObjectData", "scene.arc"]),
                b"arc_bytes",
            )

    def test_reads_binary_content_exactly(self):
        content = bytes(range(256))
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "binary.bin"), "wb") as f:
                f.write(content)
            self.assertEqual(
                self._make_builder(d).get_file_data(["binary.bin"]),
                content,
            )

    def test_missing_file_raises(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises((FileNotFoundError, OSError)):
                self._make_builder(d).get_file_data(["ghost.bin"])


if __name__ == "__main__":
    unittest.main()
