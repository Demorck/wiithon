import unittest
from file_system_table.FSTNode import FSTNode, FSTDirectory, FSTFile
from file_system_table.Operations import find_node, remove_node, add_node


class TestFindNode(unittest.TestCase):
    """Unit tests for find_node."""

    def _build_tree(self) -> list[FSTNode]:
        root = FSTDirectory("Data")
        movie = FSTDirectory("movie")
        intro = FSTFile("intro.thp", offset=0x1000, length=0x5000)
        ending = FSTFile("ending.thp", offset=0x6000, length=0x3000)
        movie.children = [intro, ending]
        root.children = [movie]
        return [root]

    def test_find_file(self) -> None:
        entries = self._build_tree()
        node = find_node(entries, ["Data", "movie", "intro.thp"])
        self.assertIsNotNone(node)
        self.assertIsInstance(node, FSTFile)
        self.assertEqual(node.name, "intro.thp")
        self.assertEqual(node.offset, 0x1000)

    def test_find_directory(self) -> None:
        entries = self._build_tree()
        node = find_node(entries, ["Data", "movie"])
        self.assertIsNotNone(node)
        self.assertIsInstance(node, FSTDirectory)

    def test_find_nonexistent(self) -> None:
        entries = self._build_tree()
        node = find_node(entries, ["Data", "sound", "bgm.brstm"])
        self.assertIsNone(node)


class TestRemoveNode(unittest.TestCase):
    """Unit tests for remove_node."""

    def _build_tree(self) -> list[FSTNode]:
        root = FSTDirectory("Data")
        movie = FSTDirectory("movie")
        intro = FSTFile("intro.thp", offset=0x1000, length=0x5000)
        ending = FSTFile("ending.thp", offset=0x6000, length=0x3000)
        movie.children = [intro, ending]
        root.children = [movie]
        return [root]

    def test_remove_file(self) -> None:
        entries = self._build_tree()
        removed = remove_node(entries, ["Data", "movie", "intro.thp"])
        self.assertIsNotNone(removed)
        self.assertIsInstance(removed, FSTFile)
        self.assertEqual(removed.name, "intro.thp")
        movie = entries[0].children[0]
        self.assertEqual(len(movie.children), 1)
        self.assertEqual(movie.children[0].name, "ending.thp")

    def test_remove_nonexistent(self) -> None:
        entries = self._build_tree()
        removed = remove_node(entries, ["Data", "movie", "nope.thp"])
        self.assertIsNone(removed)


class TestAddNode(unittest.TestCase):
    """Unit tests for add_node."""

    def _build_tree(self) -> list[FSTNode]:
        root = FSTDirectory("Data")
        movie = FSTDirectory("movie")
        intro = FSTFile("intro.thp", offset=0x1000, length=0x5000)
        movie.children = [intro]
        root.children = [movie]
        return [root]

    def test_add_file(self) -> None:
        entries = self._build_tree()
        new_file = FSTFile("credits.thp", offset=0x9000, length=0x2000)
        add_node(entries, ["Data", "movie"], new_file)
        movie = entries[0].children[0]
        names = [c.name for c in movie.children]
        self.assertIn("credits.thp", names)

    def test_add_creates_directories(self) -> None:
        entries = self._build_tree()
        new_file = FSTFile("bgm.brstm", offset=0xA000, length=0x1000)
        add_node(entries, ["Data", "sound"], new_file)
        sound = find_node(entries, ["Data", "sound"])
        self.assertIsNotNone(sound)
        self.assertIsInstance(sound, FSTDirectory)
        self.assertEqual(sound.children[0].name, "bgm.brstm")

    def test_add_replaces_existing(self) -> None:
        entries = self._build_tree()
        replacement = FSTFile("intro.thp", offset=0xF000, length=0x8000)
        old = add_node(entries, ["Data", "movie"], replacement)
        self.assertIsNotNone(old)
        self.assertIsInstance(old, FSTFile)
        self.assertEqual(old.offset, 0x1000)
        updated = find_node(entries, ["Data", "movie", "intro.thp"])
        self.assertIsInstance(updated, FSTFile)
        self.assertEqual(updated.offset, 0xF000)

    def test_add_through_file_raises(self) -> None:
        entries = self._build_tree()
        new_file = FSTFile("bug.txt")
        with self.assertRaises(ValueError):
            add_node(entries, ["Data", "movie", "intro.thp", "impossible"], new_file)


if __name__ == "__main__":
    unittest.main()