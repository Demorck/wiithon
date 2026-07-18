import unittest
from unittest.mock import MagicMock

from wiithon.builder.CopyBuilder import CopyBuilder
from wiithon.file_system_table.FST import FST
from wiithon.file_system_table.FSTNode import FSTFile, FSTDirectory
from wiithon.structs.WiiPartitionEntry import WiiPartitionEntry
from wiithon.helpers.Enums import WiiPartType


#  Helpers 

def _make_partition_info(fst_entries=None):
    """Partition info mockée avec des valeurs distinctes par getter."""
    info = MagicMock()
    info.read_bi2.return_value      = b'\xBB' * 0x2000
    info.read_apploader.return_value = b'\xAA' * 0x20

    dol = MagicMock()
    dol.to_bytes.return_value = b'\xDD' * 0x40
    info.read_dol.return_value = dol

    fst = FST()
    fst.entries = list(fst_entries or [])
    info.fst = fst

    return info


def _make_copy_builder(fst_entries=None, **kwargs):
    info = _make_partition_info(fst_entries)
    entry = WiiPartitionEntry(0, 0)
    entry.part_type = WiiPartType.DATA.value

    reader = MagicMock()
    reader.open_partition.return_value = info

    return CopyBuilder(reader, entry, **kwargs), info


#  Getters
class TestCopyBuilderGetters(unittest.TestCase):

    def setUp(self):
        self.cb, self.info = _make_copy_builder()

    def test_get_bi2(self):
        self.assertEqual(self.cb.get_bi2(), b'\xBB' * 0x2000)

    def test_get_apploader(self):
        self.assertEqual(self.cb.get_apploader(), b'\xAA' * 0x20)

    def test_get_dol_calls_to_bytes(self):
        self.assertEqual(self.cb.get_dol(), b'\xDD' * 0x40)

    def test_get_partition_type_data(self):
        self.assertEqual(self.cb.get_partition_type(), WiiPartType.DATA)

    def test_get_tmd(self):
        self.assertIs(self.cb.get_tmd(), self.info.tmd)

    def test_get_ticket(self):
        self.assertIs(self.cb.get_ticket(), self.info.header.ticket)

    def test_get_certificates(self):
        self.assertIs(self.cb.get_certificates(), self.info.certificates)

    def test_get_encrypted_header(self):
        self.assertIs(self.cb.get_encrypted_header(), self.info.internal_header)


#  fst_modifier
class TestCopyBuilderFSTModifier(unittest.TestCase):

    def test_modifier_is_called_at_construction(self):
        called = []
        _make_copy_builder(fst_modifier=lambda fst: called.append(True))
        self.assertTrue(called)

    def test_modifier_receives_fst_instance(self):
        received = []
        _make_copy_builder(fst_modifier=lambda fst: received.append(type(fst).__name__))
        self.assertEqual(received, ["FST"])

    def test_none_modifier_does_not_crash(self):
        _make_copy_builder(fst_modifier=None)

    def test_modification_reflected_in_get_fst(self):
        injected = FSTFile("injected.bin", offset=0, length=10)

        def modifier(fst):
            fst.entries.append(injected)

        cb, _ = _make_copy_builder(fst_modifier=modifier)
        names = [e.name for e in cb.get_fst().entries]
        self.assertIn("injected.bin", names)


#  dol_modifier
class TestCopyBuilderDOLModifier(unittest.TestCase):
    def test_modifier_is_called_at_construction(self):
        called = []
        _make_copy_builder(dol_modifier=lambda dol: called.append(True))
        self.assertTrue(called)

    def test_modifier_receives_dol_object(self):
        received = []
        cb, info = _make_copy_builder(
            dol_modifier=lambda dol: received.append(dol)
        )
        self.assertIs(received[0], info.read_dol.return_value)

    def test_none_modifier_does_not_crash(self):
        _make_copy_builder(dol_modifier=None)


#  get_file_data
class TestCopyBuilderGetFileData(unittest.TestCase):

    def test_override_takes_precedence_over_fst(self):
        fst_file = FSTFile("file.arc", offset=0x1000, length=0x100)
        cb, info = _make_copy_builder(
            fst_entries=[fst_file],
            file_overrides={"file.arc": b"override_data"},
        )
        self.assertEqual(cb.get_file_data(["file.arc"]), b"override_data")

    def test_override_does_not_call_crypto(self):
        cb, info = _make_copy_builder(file_overrides={"file.arc": b"data"})
        cb.get_file_data(["file.arc"])
        info.crypto.read_at.assert_not_called()

    def test_override_with_subpath(self):
        cb, _ = _make_copy_builder(
            file_overrides={"ObjectData/scene.arc": b"scene"}
        )
        self.assertEqual(
            cb.get_file_data(["ObjectData", "scene.arc"]), b"scene"
        )

    def test_fst_lookup_reads_from_crypto(self):
        fst_file = FSTFile("scene.bin", offset=0x4000, length=0x200)
        cb, info = _make_copy_builder(fst_entries=[fst_file])
        info.crypto.read_at.return_value = b"decrypted"

        result = cb.get_file_data(["scene.bin"])

        self.assertEqual(result, b"decrypted")
        info.crypto.read_at.assert_called_with(0x4000, 0x200)

    def test_fst_lookup_in_subdirectory(self):
        child = FSTFile("child.bin", offset=0x8000, length=0x50)
        subdir = FSTDirectory("ObjectData")
        subdir.children.append(child)
        cb, info = _make_copy_builder(fst_entries=[subdir])
        info.crypto.read_at.return_value = b"child"

        result = cb.get_file_data(["ObjectData", "child.bin"])

        self.assertEqual(result, b"child")
        info.crypto.read_at.assert_called_with(0x8000, 0x50)

    def test_unknown_path_raises_file_not_found(self):
        cb, _ = _make_copy_builder()
        with self.assertRaises(FileNotFoundError):
            cb.get_file_data(["ghost.bin"])

    def test_unknown_nested_path_raises_file_not_found(self):
        cb, _ = _make_copy_builder()
        with self.assertRaises(FileNotFoundError):
            cb.get_file_data(["Dir", "ghost.bin"])


if __name__ == "__main__":
    unittest.main()
