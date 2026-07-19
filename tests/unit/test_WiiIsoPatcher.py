import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from wiithon.WiiIsoPatcher import WiiIsoPatcher
from wiithon.file_system_table.FSTNode import FSTFile, FSTDirectory
from wiithon.helpers.Enums import WiiPartType


def _make_patcher():
    p = WiiIsoPatcher("dummy.iso")
    p.reader = MagicMock()
    p.data_partition = MagicMock()
    p.reader.disc_header.game_title = "GAME TITLE"
    return p


# list_files
class TestListFiles(unittest.TestCase):

    def test_delegates_to_data_partition(self):
        p = _make_patcher()
        p.data_partition.list_files.return_value = ["a.bin", "dir/b.arc"]
        self.assertEqual(p.list_files(), ["a.bin", "dir/b.arc"])
        p.data_partition.list_files.assert_called_once()


# read_dol
class TestReadDol(unittest.TestCase):

    def test_delegates_to_data_partition(self):
        p = _make_patcher()
        mock_dol = MagicMock()
        p.data_partition.read_dol.return_value = mock_dol
        self.assertIs(p.read_dol(), mock_dol)
        p.data_partition.read_dol.assert_called_once()


# get_info
class TestGetInfo(unittest.TestCase):

    def _setup(self, game_id=b"RMGE01", title="Super Mario Galaxy",
               disc_num=0, version=0):
        p = _make_patcher()
        p.reader.disc_header.game_id = game_id
        p.reader.disc_header.game_title = title
        p.reader.disc_header.disc_num = disc_num
        p.reader.disc_header.disc_version = version
        return p

    def test_returns_all_keys(self):
        info = self._setup().get_infos()
        for key in ("game_id", "title", "disc_number", "version"):
            self.assertIn(key, info)

    def test_game_id_decoded(self):
        self.assertEqual(self._setup(game_id=b"RMGE01").get_infos()["game_id"], "RMGE01")

    def test_game_id_null_bytes_stripped(self):
        self.assertEqual(self._setup(game_id=b"RMCE\x00\x00").get_infos()["game_id"], "RMCE")

    def test_title_preserved(self):
        self.assertEqual(self._setup(title="Super Mario Galaxy").get_infos()["title"],
                         "Super Mario Galaxy")

    def test_disc_number_and_version(self):
        info = self._setup(disc_num=1, version=2).get_infos()
        self.assertEqual(info["disc_number"], 1)
        self.assertEqual(info["version"], 2)


# add_file
class TestAddFile(unittest.TestCase):

    def test_stored_in_file_replacements(self):
        p = _make_patcher()
        p.add_file("ObjectData/New.arc", b"hello")
        self.assertEqual(p.file_replacements["ObjectData/New.arc"], b"hello")

    def test_stored_in_files_to_add(self):
        p = _make_patcher()
        p.add_file("ObjectData/New.arc", b"hello")
        self.assertEqual(p.files_to_add["ObjectData/New.arc"], b"hello")

    def test_leading_slash_stripped(self):
        p = _make_patcher()
        p.add_file("/ObjectData/New.arc", b"data")
        self.assertIn("ObjectData/New.arc", p.file_replacements)
        self.assertIn("ObjectData/New.arc", p.files_to_add)

    def test_overwrite_same_path_keeps_latest(self):
        p = _make_patcher()
        p.add_file("file.bin", b"v1")
        p.add_file("file.bin", b"v2")
        self.assertEqual(p.file_replacements["file.bin"], b"v2")
        self.assertEqual(p.files_to_add["file.bin"], b"v2")


# remove_file
class TestRemoveFile(unittest.TestCase):

    def test_appended_to_list(self):
        p = _make_patcher()
        p.remove_file("ObjectData/Old.arc")
        self.assertIn("ObjectData/Old.arc", p.files_to_remove)

    def test_leading_slash_stripped(self):
        p = _make_patcher()
        p.remove_file("/ObjectData/Old.arc")
        self.assertIn("ObjectData/Old.arc", p.files_to_remove)

    def test_add_then_remove(self):
        p = _make_patcher()
        p.add_file("/ObjectData/NewAdd.arc", b'data')
        self.assertIn("ObjectData/NewAdd.arc", p.files_to_add)
        self.assertIn("ObjectData/NewAdd.arc", p.file_replacements)

        p.remove_file("ObjectData/NewAdd.arc")
        self.assertNotIn("ObjectData/NewAdd.arc", p.files_to_add)
        self.assertNotIn("ObjectData/NewAdd.arc", p.file_replacements)
        self.assertNotIn("ObjectData/NewAdd.arc", p.files_to_remove)

    def test_multiple_calls_accumulate(self):
        p = _make_patcher()
        p.remove_file("a.bin")
        p.remove_file("b.bin")
        self.assertIn("a.bin", p.files_to_remove)
        self.assertIn("b.bin", p.files_to_remove)


# _build_fst_modifier
class TestBuildFstModifier(unittest.TestCase):

    def _fst_with(self, *entries):
        fst = MagicMock()
        fst.entries = list(entries)
        return fst

    def test_returns_none_when_nothing_configured(self):
        self.assertIsNone(_make_patcher()._build_fst_modifier())

    def test_returns_callable_with_user_modifier(self):
        p = _make_patcher()
        p.modify_fst(lambda fst: None)
        self.assertTrue(callable(p._build_fst_modifier()))

    def test_returns_callable_with_files_to_add(self):
        p = _make_patcher()
        p.add_file("file.bin", b"data")
        self.assertTrue(callable(p._build_fst_modifier()))

    def test_returns_callable_with_files_to_remove(self):
        p = _make_patcher()
        p.remove_file("file.bin")
        self.assertTrue(callable(p._build_fst_modifier()))

    def test_user_modifier_is_called(self):
        p = _make_patcher()
        called_with = []
        p.modify_fst(lambda fst: called_with.append(fst))
        fst = self._fst_with()
        p._build_fst_modifier()(fst)
        self.assertEqual(called_with, [fst])

    def test_adds_file_to_existing_directory(self):
        p = _make_patcher()
        p.add_file("ObjectData/New.arc", b"x" * 100)

        obj_dir = FSTDirectory("ObjectData")
        fst = self._fst_with(obj_dir)

        p._build_fst_modifier()(fst)

        self.assertTrue(any(
            isinstance(n, FSTFile) and n.name == "New.arc" and n.length == 100
            for n in obj_dir.children
        ))

    def test_adds_file_at_root(self):
        p = _make_patcher()
        p.add_file("root.bin", b"y" * 42)
        fst = self._fst_with()

        p._build_fst_modifier()(fst)

        self.assertTrue(any(
            isinstance(n, FSTFile) and n.name == "root.bin" and n.length == 42
            for n in fst.entries
        ))

    def test_creates_missing_parent_directory(self):
        p = _make_patcher()
        p.add_file("NewDir/file.bin", b"z")
        fst = self._fst_with()

        p._build_fst_modifier()(fst)

        dirs = [n for n in fst.entries if isinstance(n, FSTDirectory)]
        self.assertTrue(any(d.name == "NewDir" for d in dirs))
        new_dir = next(d for d in dirs if d.name == "NewDir")
        self.assertTrue(any(c.name == "file.bin" for c in new_dir.children))

    def test_removes_existing_file(self):
        p = _make_patcher()
        p.remove_file("ObjectData/Old.arc")

        obj_dir = FSTDirectory("ObjectData")
        obj_dir.children.append(FSTFile("Old.arc", offset=0, length=100))
        fst = self._fst_with(obj_dir)

        p._build_fst_modifier()(fst)

        self.assertFalse(any(n.name == "Old.arc" for n in obj_dir.children))

    def test_remove_nonexistent_file_does_not_crash(self):
        p = _make_patcher()
        p.remove_file("ghost.bin")
        fst = self._fst_with()
        p._build_fst_modifier()(fst)

    def test_snapshots_files_to_add_at_call_time(self):
        p = _make_patcher()
        p.add_file("first.bin", b"a")
        modifier = p._build_fst_modifier()

        p.add_file("second.bin", b"b")   # après le snapshot

        fst = self._fst_with()
        modifier(fst)

        names = [n.name for n in fst.entries]
        self.assertIn("first.bin", names)
        self.assertNotIn("second.bin", names)


# build()
class TestBuildIntegration(unittest.TestCase):

    def _make_reader_mock(self):
        entry = MagicMock()
        entry.part_type = WiiPartType.DATA
        reader = MagicMock()
        reader.partitions = [entry]
        return reader

    @patch("wiithon.WiiIsoPatcher.WiiDiscBuilder")
    @patch("wiithon.WiiIsoPatcher.CopyBuilder")
    def test_fst_modifier_not_none_when_add_file_called(self, MockCopyBuilder, _):
        p = WiiIsoPatcher("dummy.iso")
        p.reader = self._make_reader_mock()
        p.data_partition = MagicMock()
        p.add_file("new.bin", b"data")

        with tempfile.TemporaryDirectory() as tmp:
            p.build(os.path.join(tmp, "out.iso"))

        _, kwargs = MockCopyBuilder.call_args
        self.assertIsNotNone(kwargs.get("fst_modifier"))

    @patch("wiithon.WiiIsoPatcher.WiiDiscBuilder")
    @patch("wiithon.WiiIsoPatcher.CopyBuilder")
    def test_fst_modifier_is_none_when_nothing_configured(self, MockCopyBuilder, _):
        p = WiiIsoPatcher("dummy.iso")
        p.reader = self._make_reader_mock()
        p.data_partition = MagicMock()

        with tempfile.TemporaryDirectory() as tmp:
            p.build(os.path.join(tmp, "out.iso"))

        _, kwargs = MockCopyBuilder.call_args
        self.assertIsNone(kwargs.get("fst_modifier"))


if __name__ == "__main__":
    unittest.main()
