import unittest
from io import BytesIO
from unittest.mock import MagicMock

from wiithon.WiiIsoPatcher import WiiIsoPatcher
from wiithon.file_helper.rarc import Rarc, RarcNode, RarcFileEntry
from wiithon.file_helper.yaz0 import Yaz0
from wiithon.file_helper.resolver_path import resolve_read, resolve_write


def _rarc_entry(name: str, file_id: int, is_dir: bool,
                data: bytes = b"", node_idx: int = 0) -> RarcFileEntry:
    e = RarcFileEntry()
    e.name = name
    e.file_id = 0xFFFF if is_dir else file_id
    e.type = 0x02 if is_dir else 0x11
    e.data_offset_or_idx = node_idx
    e.data = data
    e.data_size = len(data)
    return e


def build_flat_rarc(files: dict[str, bytes]) -> bytes:
    rarc = Rarc()

    root = RarcNode()
    root.type = "ROOT"
    root.first_entry_index = 0
    root.entry_count = 2 + len(files)
    rarc.nodes.append(root)

    rarc.entries.append(_rarc_entry(".", 0xFFFF, is_dir=True, node_idx=0))
    rarc.entries.append(_rarc_entry("..", 0xFFFF, is_dir=True, node_idx=0))
    for fid, (name, data) in enumerate(files.items()):
        rarc.entries.append(_rarc_entry(name, fid, is_dir=False, data=data))

    buf = BytesIO()
    rarc.write(buf)
    return buf.getvalue()


def build_nested_rarc(subdir: str, files: dict[str, bytes]) -> bytes:
    rarc = Rarc()

    root = RarcNode()
    root.type = "ROOT"
    root.first_entry_index = 0
    root.entry_count = 3           # ".", "..", subdir
    rarc.nodes.append(root)

    sub = RarcNode()
    sub.type = subdir[:4].upper()
    sub.first_entry_index = 3
    sub.entry_count = 2 + len(files)
    rarc.nodes.append(sub)

    rarc.entries.append(_rarc_entry(".", 0xFFFF, is_dir=True, node_idx=0))
    rarc.entries.append(_rarc_entry("..", 0xFFFF, is_dir=True, node_idx=0))
    rarc.entries.append(_rarc_entry(subdir, 0xFFFF, is_dir=True, node_idx=1))

    rarc.entries.append(_rarc_entry(".", 0xFFFF, is_dir=True, node_idx=1))
    rarc.entries.append(_rarc_entry("..", 0xFFFF, is_dir=True, node_idx=0))
    for fid, (name, data) in enumerate(files.items()):
        rarc.entries.append(_rarc_entry(name, fid, is_dir=False, data=data))

    buf = BytesIO()
    rarc.write(buf)
    return buf.getvalue()


def build_yaz0_rarc(files: dict[str, bytes]) -> bytes:
    raw = build_flat_rarc(files)
    buf = BytesIO()
    Yaz0.from_data(raw).write(buf)
    return buf.getvalue()


def make_patcher(fst_files: dict[str, bytes]) -> WiiIsoPatcher:
    p = WiiIsoPatcher.__new__(WiiIsoPatcher)
    p.src_path = ""
    p.reader = None
    p.dol_modifier = None
    p.fst_modifier = None
    p.file_replacements = {}
    p.files_to_add = {}
    p.files_to_remove = []

    dp = MagicMock()
    dp.read_file.side_effect = lambda path: fst_files[path.strip("/")]

    fst = MagicMock()
    def find_node(parts):
        if isinstance(parts, str):
            parts = [x for x in parts.strip("/").split("/") if x]
        joined = "/".join(parts)
        if joined in fst_files:
            node = MagicMock()
            node.is_file = True
            node.is_directory = False
            return node
        return None
    fst.find_node.side_effect = find_node
    dp.fst = fst

    p.data_partition = dp
    return p


class SimpleData:
    def __init__(self, value: int = 0):
        self.value = value

    @classmethod
    def read(cls, stream: BytesIO) -> "SimpleData":
        return cls(int.from_bytes(stream.read(4), "big"))

    def write(self, stream: BytesIO) -> None:
        stream.write(self.value.to_bytes(4, "big"))


class TestResolveRead(unittest.TestCase):
    def test_direct_fst_file(self):
        payload = b"\x01\x02\x03\x04"
        p = make_patcher({"opening.bnr": payload})
        self.assertEqual(resolve_read(p, "opening.bnr"), payload)

    def test_flat_rarc(self):
        rarc_bytes = build_flat_rarc({"myfile.bin": b"hello"})
        p = make_patcher({"Mario.arc": rarc_bytes})
        self.assertEqual(resolve_read(p, "Mario.arc/myfile.bin"), b"hello")

    def test_yaz0_rarc(self):
        rarc_bytes = build_yaz0_rarc({"data.bin": b"compressed_content"})
        p = make_patcher({"Stage.szs": rarc_bytes})
        self.assertEqual(resolve_read(p, "Stage.szs/data.bin"), b"compressed_content")

    def test_nested_subdir(self):
        rarc_bytes = build_nested_rarc("layera", {"objinfo": b"\xAB\xCD"})
        p = make_patcher({"AstroGalaxy.arc": rarc_bytes})
        self.assertEqual(resolve_read(p, "AstroGalaxy.arc/layera/objinfo"), b"\xAB\xCD")

    def test_fst_path_not_found(self):
        p = make_patcher({})
        with self.assertRaises(FileNotFoundError):
            resolve_read(p, "missing.arc/file.bin")

    def test_file_not_found_in_rarc(self):
        rarc_bytes = build_flat_rarc({"real.bin": b"data"})
        p = make_patcher({"Mario.arc": rarc_bytes})
        with self.assertRaises(FileNotFoundError):
            resolve_read(p, "Mario.arc/missing.bin")


class TestResolveWrite(unittest.TestCase):
    def test_direct_fst_file(self):
        p = make_patcher({"opening.bnr": b"\x00" * 4})
        resolve_write(p, "opening.bnr", b"\xFF" * 4)
        self.assertEqual(p.file_replacements["opening.bnr"], b"\xFF" * 4)

    def test_flat_rarc_roundtrip(self):
        rarc_bytes = build_flat_rarc({"myfile.bin": b"original"})
        p = make_patcher({"Mario.arc": rarc_bytes})

        resolve_write(p, "Mario.arc/myfile.bin", b"modified")

        self.assertIn("Mario.arc", p.file_replacements)
        updated = Rarc.read(BytesIO(p.file_replacements["Mario.arc"]))
        self.assertEqual(updated.get_file("myfile.bin"), b"modified")

    def test_yaz0_rarc_roundtrip(self):
        rarc_bytes = build_yaz0_rarc({"data.bin": b"original"})
        p = make_patcher({"Stage.szs": rarc_bytes})

        resolve_write(p, "Stage.szs/data.bin", b"new_content")

        result = p.file_replacements["Stage.szs"]
        self.assertEqual(result[:4], b"Yaz0", "Le résultat doit rester compressé en Yaz0")
        yaz0 = Yaz0.read(BytesIO(result))
        rarc = Rarc.read(BytesIO(yaz0.data))
        self.assertEqual(rarc.get_file("data.bin"), b"new_content")

    def test_nested_subdir_roundtrip(self):
        rarc_bytes = build_nested_rarc("layera", {"objinfo": b"\x00\x00"})
        p = make_patcher({"AstroGalaxy.arc": rarc_bytes})

        resolve_write(p, "AstroGalaxy.arc/layera/objinfo", b"\xFF\xFF")

        rarc = Rarc.read(BytesIO(p.file_replacements["AstroGalaxy.arc"]))
        self.assertEqual(rarc.get_file_by_path("layera/objinfo"), b"\xFF\xFF")

    def test_does_not_touch_other_files_in_rarc(self):
        rarc_bytes = build_flat_rarc({"a.bin": b"AAA", "b.bin": b"BBB"})
        p = make_patcher({"Mario.arc": rarc_bytes})

        resolve_write(p, "Mario.arc/a.bin", b"ZZZ")

        rarc = Rarc.read(BytesIO(p.file_replacements["Mario.arc"]))
        self.assertEqual(rarc.get_file("b.bin"), b"BBB")


class TestEditAs(unittest.TestCase):
    def test_direct_fst_read_and_modify(self):
        initial = (42).to_bytes(4, "big")
        p = make_patcher({"data.bin": initial})

        with p.edit_as("data.bin", SimpleData) as obj:
            self.assertEqual(obj.value, 42)
            obj.value = 99

        self.assertEqual(int.from_bytes(p.file_replacements["data.bin"], "big"), 99)

    def test_archive_read_and_modify(self):
        initial = (10).to_bytes(4, "big")
        rarc_bytes = build_flat_rarc({"table.bin": initial})
        p = make_patcher({"Stage.arc": rarc_bytes})

        with p.edit_as("Stage.arc/table.bin", SimpleData) as obj:
            self.assertEqual(obj.value, 10)
            obj.value = 200

        rarc = Rarc.read(BytesIO(p.file_replacements["Stage.arc"]))
        self.assertEqual(int.from_bytes(rarc.get_file("table.bin"), "big"), 200)

    def test_no_modification_still_replaces(self):
        initial = (5).to_bytes(4, "big")
        p = make_patcher({"data.bin": initial})

        with p.edit_as("data.bin", SimpleData):
            pass

        self.assertIn("data.bin", p.file_replacements)
        self.assertEqual(int.from_bytes(p.file_replacements["data.bin"], "big"), 5)

    def test_exception_in_block_does_not_replace(self):
        initial = (1).to_bytes(4, "big")
        p = make_patcher({"data.bin": initial})

        with self.assertRaises(ValueError):
            with p.edit_as("data.bin", SimpleData) as obj:
                obj.value = 999
                raise ValueError("erreur intentionnelle")

        self.assertNotIn("data.bin", p.file_replacements)

    def test_sequential_edit_as_on_same_archive(self):
        fst_files = {
            "Stage.arc": build_flat_rarc({
                "a.bin": (1).to_bytes(4, "big"),
                "b.bin": (2).to_bytes(4, "big"),
            })
        }
        p = make_patcher(fst_files)

        with p.edit_as("Stage.arc/a.bin", SimpleData) as obj:
            obj.value = 10

        # Le second edit_as doit voir l'archive déjà modifiée
        fst_files["Stage.arc"] = p.file_replacements["Stage.arc"]

        with p.edit_as("Stage.arc/b.bin", SimpleData) as obj:
            obj.value = 20

        rarc = Rarc.read(BytesIO(p.file_replacements["Stage.arc"]))
        self.assertEqual(int.from_bytes(rarc.get_file("a.bin"), "big"), 10)
        self.assertEqual(int.from_bytes(rarc.get_file("b.bin"), "big"), 20)

    def test_yaz0_archive_edit_as(self):
        initial = (77).to_bytes(4, "big")
        rarc_bytes = build_yaz0_rarc({"config.bin": initial})
        p = make_patcher({"Stage.szs": rarc_bytes})

        with p.edit_as("Stage.szs/config.bin", SimpleData) as obj:
            obj.value = 88

        result = p.file_replacements["Stage.szs"]
        self.assertEqual(result[:4], b"Yaz0")
        yaz0 = Yaz0.read(BytesIO(result))
        rarc = Rarc.read(BytesIO(yaz0.data))
        self.assertEqual(int.from_bytes(rarc.get_file("config.bin"), "big"), 88)


class TestAutoDetectLastFile(unittest.TestCase):
    def test_single_file_in_dir_auto_selected(self):
        rarc_bytes = build_nested_rarc("layera", {"objinfo": b"unique"})
        rarc = Rarc.read(BytesIO(rarc_bytes))
        self.assertEqual(rarc.get_file_by_path("layera"), b"unique")

    def test_multiple_files_in_dir_raises(self):
        rarc_bytes = build_nested_rarc("layera", {"file1.bin": b"A", "file2.bin": b"B"})
        rarc = Rarc.read(BytesIO(rarc_bytes))
        with self.assertRaisesRegex(ValueError, "file1.bin|file2.bin"):
            rarc.get_file_by_path("layera")

    def test_explicit_file_path_unchanged(self):
        rarc_bytes = build_nested_rarc("layera", {"objinfo": b"data"})
        rarc = Rarc.read(BytesIO(rarc_bytes))
        self.assertEqual(rarc.get_file_by_path("layera/objinfo"), b"data")


if __name__ == "__main__":
    unittest.main()
