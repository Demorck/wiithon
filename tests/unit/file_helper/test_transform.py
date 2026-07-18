import os
import sys
import unittest
from io import BytesIO
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from wiithon.file_helper.rarc import Rarc, RarcNode, RarcFileEntry
from wiithon.file_helper.yaz0 import Yaz0
from wiithon.file_helper.transforms import yaz0_transform, rarc_transform, auto_yaz0_transform
from wiithon.WiiIsoPatcher import WiiIsoPatcher

# May need to break this file into smaller ones

# Helpers
def _make_rarc_bytes(files: dict[str, bytes]) -> bytes:
    rarc = Rarc()

    root = RarcNode()
    root.type = "ROOT"
    root.entry_count = 1 + len(files)  # . + files
    root.first_entry_index = 0
    rarc.nodes.append(root)

    dot = RarcFileEntry()
    dot.file_id = 0xFFFF
    dot.type = 0x02
    dot.name = "."
    rarc.entries.append(dot)

    for i, (name, data) in enumerate(files.items()):
        entry = RarcFileEntry()
        entry.file_id = i
        entry.type = 0x11
        entry.name = name
        entry.data = data
        rarc.entries.append(entry)

    buf = BytesIO()
    rarc.write(buf)
    return buf.getvalue()


def _make_yaz0_bytes(data: bytes) -> bytes:
    buf = BytesIO()
    Yaz0.from_data(data).write(buf)
    return buf.getvalue()


# Rarc.get_file / replace_file

class TestRarcGetFile(unittest.TestCase):

    def setUp(self):
        data = _make_rarc_bytes({"scene.bcsv": b"original_data", "other.bin": b"other"})
        self.rarc = Rarc.read(BytesIO(data))

    def test_returns_correct_data(self):
        self.assertEqual(self.rarc.get_file("scene.bcsv"), b"original_data")

    def test_raises_for_unknown_name(self):
        with self.assertRaises(FileNotFoundError):
            self.rarc.get_file("ghost.bcsv")

    def test_does_not_return_dot_entry(self):
        with self.assertRaises(FileNotFoundError):
            self.rarc.get_file(".")


class TestRarcReplaceFile(unittest.TestCase):
    def setUp(self):
        data = _make_rarc_bytes({"scene.bcsv": b"original_data"})
        self.rarc = Rarc.read(BytesIO(data))

    def test_updates_entry_data(self):
        self.rarc.replace_file("scene.bcsv", b"new_data")
        self.assertEqual(self.rarc.get_file("scene.bcsv"), b"new_data")

    def test_raises_for_unknown_name(self):
        with self.assertRaises(FileNotFoundError):
            self.rarc.replace_file("ghost.bcsv", b"data")

    def test_persists_after_write_read_round_trip(self):
        self.rarc.replace_file("scene.bcsv", b"round_trip_data")
        buf = BytesIO()
        self.rarc.write(buf)
        buf.seek(0)
        reloaded = Rarc.read(buf)
        self.assertEqual(reloaded.get_file("scene.bcsv"), b"round_trip_data")


# rarc_transform
class TestRarcTransform(unittest.TestCase):

    def setUp(self):
        self.rarc_bytes = _make_rarc_bytes({"scene.bcsv": b"hello"})

    def test_inner_receives_rarc_instance(self):
        received = []
        rarc_transform(lambda r: received.append(type(r).__name__))(self.rarc_bytes)
        self.assertEqual(received, ["Rarc"])

    def test_modifications_visible_in_output(self):
        def patch(rarc):
            rarc.replace_file("scene.bcsv", b"patched")

        result = rarc_transform(patch)(self.rarc_bytes)
        reloaded = Rarc.read(BytesIO(result))
        self.assertEqual(reloaded.get_file("scene.bcsv"), b"patched")

    def test_output_is_valid_rarc(self):
        result = rarc_transform(lambda r: None)(self.rarc_bytes)
        rarc = Rarc.read(BytesIO(result))
        self.assertEqual(rarc.magic_word, "RARC")

    def test_unmodified_file_is_preserved(self):
        rarc_bytes = _make_rarc_bytes({"a.bin": b"aaa", "b.bin": b"bbb"})

        def patch(rarc):
            rarc.replace_file("a.bin", b"new_a")

        result = rarc_transform(patch)(rarc_bytes)
        reloaded = Rarc.read(BytesIO(result))
        self.assertEqual(reloaded.get_file("b.bin"), b"bbb")


# yaz0_transform
class TestYaz0Transform(unittest.TestCase):

    def setUp(self):
        self.raw = b"Super Mario Galaxy " * 50
        self.yaz0_bytes = _make_yaz0_bytes(self.raw)

    def test_inner_receives_decompressed_data(self):
        received = []
        yaz0_transform(lambda d: received.append(d) or d)(self.yaz0_bytes)
        self.assertEqual(received[0], self.raw)

    def test_output_starts_with_yaz0_magic(self):
        result = yaz0_transform(lambda d: d)(self.yaz0_bytes)
        self.assertEqual(result[:4], b"Yaz0")

    def test_round_trip_preserves_data(self):
        result = yaz0_transform(lambda d: d)(self.yaz0_bytes)
        reloaded = Yaz0.read(BytesIO(result))
        self.assertEqual(reloaded.data, self.raw)

    def test_inner_modification_is_reflected(self):
        result = yaz0_transform(lambda d: b"replaced")(self.yaz0_bytes)
        reloaded = Yaz0.read(BytesIO(result))
        self.assertEqual(reloaded.data, b"replaced")


#auto_yaz0_transform
class TestAutoYaz0Transform(unittest.TestCase):

    def setUp(self):
        self.raw = b"raw data not compressed " * 20
        self.yaz0_bytes = _make_yaz0_bytes(self.raw)

    def test_decompresses_when_yaz0_magic_present(self):
        received = []
        auto_yaz0_transform(lambda d: received.append(d) or d)(self.yaz0_bytes)
        self.assertEqual(received[0], self.raw)

    def test_passthrough_when_not_yaz0(self):
        received = []
        auto_yaz0_transform(lambda d: received.append(d) or d)(self.raw)
        self.assertEqual(received[0], self.raw)

    def test_output_is_yaz0_compressed_when_input_was_yaz0(self):
        result = auto_yaz0_transform(lambda d: d)(self.yaz0_bytes)
        self.assertEqual(result[:4], b"Yaz0")

    def test_output_is_raw_when_input_was_raw(self):
        result = auto_yaz0_transform(lambda d: d)(self.raw)
        self.assertNotEqual(result[:4], b"Yaz0")
        self.assertEqual(result, self.raw)


#  Yaz0 + RARC

class TestComposedTransforms(unittest.TestCase):

    def test_yaz0_rarc_chain(self):
        rarc_bytes = _make_rarc_bytes({"data.bin": b"before"})
        compressed = _make_yaz0_bytes(rarc_bytes)

        def patch(rarc):
            rarc.replace_file("data.bin", b"after")

        result = auto_yaz0_transform(rarc_transform(patch))(compressed)

        self.assertEqual(result[:4], b"Yaz0")

        decompressed = Yaz0.read(BytesIO(result)).data
        reloaded = Rarc.read(BytesIO(decompressed))
        self.assertEqual(reloaded.get_file("data.bin"), b"after")

    def test_raw_rarc_chain(self):
        rarc_bytes = _make_rarc_bytes({"data.bin": b"before"})

        def patch(rarc):
            rarc.replace_file("data.bin", b"after")

        result = auto_yaz0_transform(rarc_transform(patch))(rarc_bytes)

        reloaded = Rarc.read(BytesIO(result))
        self.assertEqual(reloaded.get_file("data.bin"), b"after")


# WiiIsoPatcher.transform_file
class TestTransformFile(unittest.TestCase):

    def _make_patcher(self):
        p = WiiIsoPatcher("dummy.iso")
        p.reader = MagicMock()
        p.data_partition = MagicMock()
        return p

    def test_reads_from_data_partition(self):
        p = self._make_patcher()
        p.data_partition.read_file.return_value = b"original"
        p.transform_file("path/to/file.bin", lambda d: d)
        p.data_partition.read_file.assert_called_once_with("path/to/file.bin")

    def test_fn_receives_original_bytes(self):
        p = self._make_patcher()
        p.data_partition.read_file.return_value = b"original"
        received = []
        p.transform_file("file.bin", lambda d: received.append(d) or d)
        self.assertEqual(received[0], b"original")

    def test_fn_result_stored_in_replacements(self):
        p = self._make_patcher()
        p.data_partition.read_file.return_value = b"original"
        p.transform_file("path/file.bin", lambda d: b"transformed")
        self.assertEqual(p.file_replacements["path/file.bin"], b"transformed")


if __name__ == "__main__":
    unittest.main()
