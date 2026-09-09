import hashlib
import struct
import unittest
from io import BytesIO

from wiithon.exceptions import ArchiveFileNotFoundError, InvalidFormatError
from wiithon.formats.bnr import BNR
from wiithon.formats.imet import (
    IMET_BLOCK_SIZE,
    IMET_LANGUAGES,
    IMET_MAGIC_WORD,
    IMET_PADDING_SIZE,
    IMET_TITLE_MAX_BYTES,
)
from wiithon.formats.u8 import U8, U8Node

U8_OFFSET = IMET_PADDING_SIZE + IMET_BLOCK_SIZE
MD5_OFFSET = 0x5B0

TITLE = "SUPER MARIO GALAXY"
ICON_SIZE = 0x1000
BANNER_SIZE = 0x2000
SOUND_SIZE = 0x3000

FILES = {
    "icon.bin":   b'\xAA' * 0x80,
    "banner.bin": b'\xBB' * 0x100,
    "sound.bin":  b'\xCC' * 0x40,
}


def _build_imet() -> bytes:
    block = bytearray(IMET_BLOCK_SIZE)
    block[0x00:0x04] = IMET_MAGIC_WORD
    struct.pack_into(">I", block, 0x04, U8_OFFSET)
    struct.pack_into(">I", block, 0x08, 0x03) # version, nobody uses it iirc
    struct.pack_into(">III", block, 0x0C, ICON_SIZE, BANNER_SIZE, SOUND_SIZE)

    offset = 0x1C + IMET_LANGUAGES.index("English") * IMET_TITLE_MAX_BYTES
    encoded = TITLE.encode("utf-16-be")
    block[offset:offset + len(encoded)] = encoded

    header = b'\x00' * IMET_PADDING_SIZE + bytes(block)
    block[MD5_OFFSET:MD5_OFFSET + 0x10] = hashlib.md5(header).digest()

    return b'\x00' * IMET_PADDING_SIZE + bytes(block)


def _build_u8() -> bytes:
    u8 = U8()
    total_nodes = 2 + len(FILES)

    for name in ("", "meta"):
        directory = U8Node()
        directory.is_dir = True
        directory.name = name
        directory.size = total_nodes
        u8.nodes.append(directory)

    for name, data in FILES.items():
        node = U8Node()
        node.name = name
        node.data = data
        node.size = len(data)
        u8.nodes.append(node)

    return u8.get_bytes()


def _build_bnr() -> bytes:
    return _build_imet() + _build_u8()


class TestBNRRead(unittest.TestCase):

    def setUp(self):
        self.raw = _build_bnr()
        self.bnr = BNR.read(BytesIO(self.raw))

    def test_title(self):
        self.assertEqual(self.bnr.title, TITLE)

    def test_imet_sizes(self):
        self.assertEqual(self.bnr.imet.icon_size, ICON_SIZE)
        self.assertEqual(self.bnr.imet.banner_size, BANNER_SIZE)
        self.assertEqual(self.bnr.imet.sound_size, SOUND_SIZE)

    def test_get_icon(self):
        self.assertEqual(self.bnr.get_icon(), FILES["icon.bin"])

    def test_get_banner(self):
        self.assertEqual(self.bnr.get_banner(), FILES["banner.bin"])

    def test_get_sound(self):
        self.assertEqual(self.bnr.get_sound(), FILES["sound.bin"])

    def test_missing_file_raises(self):
        with self.assertRaises(ArchiveFileNotFoundError):
            self.bnr.u8.get_file("meta/ghost.bin")

    def test_bad_u8_magic_raises(self):
        broken = bytearray(self.raw)
        broken[U8_OFFSET:U8_OFFSET + 4] = b'\x00' * 4
        with self.assertRaises(InvalidFormatError):
            BNR.read(BytesIO(bytes(broken)))


class TestBNRWrite(unittest.TestCase):

    def setUp(self):
        self.raw = _build_bnr()
        self.bnr = BNR.read(BytesIO(self.raw))

    def test_roundtrip_is_byte_identical(self):
        self.assertEqual(self.bnr.get_bytes(), self.raw)

    def test_u8_still_starts_at_0x600(self):
        self.assertEqual(self.bnr.get_bytes()[U8_OFFSET:U8_OFFSET + 4], self.raw[U8_OFFSET:U8_OFFSET + 4])

    def test_set_title_then_reread(self):
        self.bnr.imet.set_title("FEUR", "English")
        again = BNR.read(BytesIO(self.bnr.get_bytes()))
        self.assertEqual(again.title, "FEUR")
        self.assertEqual(again.get_icon(), FILES["icon.bin"])

    def test_replace_icon(self):
        self.bnr.replace_icon(b'\xDE\xAD\xBE\xEF' * 8)
        again = BNR.read(BytesIO(self.bnr.get_bytes()))
        self.assertEqual(again.get_icon(), b'\xDE\xAD\xBE\xEF' * 8)
        self.assertEqual(again.imet.icon_size, 0x20)

    def test_replace_icon_keeps_the_other_files(self):
        self.bnr.replace_icon(b'\x01' * 0x10)
        again = BNR.read(BytesIO(self.bnr.get_bytes()))
        self.assertEqual(again.get_banner(), FILES["banner.bin"])
        self.assertEqual(again.get_sound(), FILES["sound.bin"])

    def test_replace_banner(self):
        self.bnr.replace_banner(b'\x02' * 0x40)
        again = BNR.read(BytesIO(self.bnr.get_bytes()))
        self.assertEqual(again.get_banner(), b'\x02' * 0x40)
        self.assertEqual(again.imet.banner_size, 0x40)
        self.assertEqual(again.imet.icon_size, ICON_SIZE)

    def test_replace_sound(self):
        self.bnr.replace_sound(b'\x03' * 0x40)
        again = BNR.read(BytesIO(self.bnr.get_bytes()))
        self.assertEqual(again.get_sound(), b'\x03' * 0x40)
        self.assertEqual(again.imet.sound_size, 0x40)
        self.assertEqual(again.imet.icon_size, ICON_SIZE)


if __name__ == "__main__":
    unittest.main()