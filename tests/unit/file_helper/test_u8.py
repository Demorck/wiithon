import struct
import unittest
from io import BytesIO

from wiithon.file_helper.u8 import U8, NODE_SIZE, ROOTNODE_OFFSET
from wiithon.helpers.Constants import U8_MAGIC_WORD
from wiithon.helpers.Utils import align


def _build_u8(files: dict[str, bytes]) -> bytes:
    names = ["", "meta"] + list(files.keys())
    file_data_list = list(files.values())
    total_nodes = 2 + len(files)

    string_table = bytearray()
    name_offsets: list[int] = []
    for name in names:
        name_offsets.append(len(string_table))
        string_table.extend(name.encode('ascii') + b'\x00')

    header_size  = total_nodes * NODE_SIZE + len(string_table)
    data_section = align(ROOTNODE_OFFSET + header_size, 0x40)

    file_offsets: list[int] = []
    cursor = data_section
    for data in file_data_list:
        file_offsets.append(cursor)
        cursor = align(cursor + len(data), 0x20)

    out = BytesIO()
    out.write(U8_MAGIC_WORD)
    out.write(struct.pack(">I", ROOTNODE_OFFSET))
    out.write(struct.pack(">I", header_size))
    out.write(struct.pack(">I", data_section))
    out.write(b'\x00' * 16)

    def _node(is_dir: bool, name_off: int, data_off: int, size: int) -> None:
        t = (0x01 if is_dir else 0x00) << 24
        out.write(struct.pack(">I", t | (name_off & 0xFFFFFF)))
        out.write(struct.pack(">I", data_off))
        out.write(struct.pack(">I", size))

    _node(True,  name_offsets[0], 0, total_nodes)
    _node(True,  name_offsets[1], 0, total_nodes)
    for i, (_, data) in enumerate(files.items()):
        _node(False, name_offsets[2 + i], file_offsets[i], len(data))

    out.write(string_table)
    out.write(b'\x00' * (data_section - ROOTNODE_OFFSET - header_size))

    written = data_section
    for data in file_data_list:
        out.write(data)
        next_a = align(written + len(data), 0x20)
        out.write(b'\x00' * (next_a - written - len(data)))
        written = next_a

    return out.getvalue()


SAMPLE = {
    "icon.bin":   b'\xAA' * 0x80,
    "banner.bin": b'\xBB' * 0x100,
    "sound.bin":  b'\xCC' * 0x40,
}


class TestU8Read(unittest.TestCase):

    def setUp(self):
        self.u8 = U8.read(BytesIO(_build_u8(SAMPLE)))

    def test_get_icon(self):
        self.assertEqual(self.u8.get_file("meta/icon.bin"), b'\xAA' * 0x80)

    def test_get_banner(self):
        self.assertEqual(self.u8.get_file("meta/banner.bin"), b'\xBB' * 0x100)

    def test_get_sound(self):
        self.assertEqual(self.u8.get_file("meta/sound.bin"), b'\xCC' * 0x40)

    def test_missing_file_raises(self):
        with self.assertRaises(FileNotFoundError):
            self.u8.get_file("meta/ghost.bin")

    def test_directory_path_raises(self):
        with self.assertRaises(FileNotFoundError):
            self.u8.get_file("meta")


class TestU8Replace(unittest.TestCase):

    def setUp(self):
        self.u8 = U8.read(BytesIO(_build_u8(SAMPLE)))

    def test_replace_updates_content(self):
        self.u8.replace_file("meta/icon.bin", b'\xFF' * 0x20)
        self.assertEqual(self.u8.get_file("meta/icon.bin"), b'\xFF' * 0x20)

    def test_replace_does_not_affect_other_files(self):
        self.u8.replace_file("meta/icon.bin", b'\xFF' * 0x20)
        self.assertEqual(self.u8.get_file("meta/banner.bin"), b'\xBB' * 0x100)

    def test_replace_missing_raises(self):
        with self.assertRaises(FileNotFoundError):
            self.u8.replace_file("meta/ghost.bin", b'\x00')


class TestU8Roundtrip(unittest.TestCase):

    def _rt(self, files: dict[str, bytes]) -> U8:
        return U8.read(BytesIO(U8.read(BytesIO(_build_u8(files))).get_bytes()))

    def test_content_preserved(self):
        u8 = self._rt(SAMPLE)
        self.assertEqual(u8.get_file("meta/icon.bin"),   b'\xAA' * 0x80)
        self.assertEqual(u8.get_file("meta/banner.bin"), b'\xBB' * 0x100)
        self.assertEqual(u8.get_file("meta/sound.bin"),  b'\xCC' * 0x40)

    def test_replace_then_roundtrip(self):
        u8 = U8.read(BytesIO(_build_u8(SAMPLE)))
        u8.replace_file("meta/icon.bin", b'\xDE\xAD\xBE\xEF' * 8)
        u8b = U8.read(BytesIO(u8.get_bytes()))
        self.assertEqual(u8b.get_file("meta/icon.bin"),   b'\xDE\xAD\xBE\xEF' * 8)
        self.assertEqual(u8b.get_file("meta/banner.bin"), b'\xBB' * 0x100)

    def test_magic_preserved(self):
        out = U8.read(BytesIO(_build_u8(SAMPLE))).get_bytes()
        self.assertEqual(out[:4], U8_MAGIC_WORD)

    def test_data_section_aligned_to_0x40(self):
        out = U8.read(BytesIO(_build_u8(SAMPLE))).get_bytes()
        data_section = struct.unpack_from(">I", out, 12)[0]
        self.assertEqual(data_section % 0x40, 0)


if __name__ == "__main__":
    unittest.main()
