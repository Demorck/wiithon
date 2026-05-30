import struct
import unittest
from io import BytesIO

from wiithon.structs.IMET import (
    IMET, MAGIC, PADDING_SIZE, IMET_BLOCK_SIZE, TITLE_COUNT, TITLE_MAX_CHARS
)


def _make_imet_bytes(
    titles: list[str] | None = None,
    icon_size: int = 0x1000,
    banner_size: int = 0x2000,
    sound_size: int = 0x3000,
    content_offset: int = 0x600,
) -> bytes:
    block = bytearray(IMET_BLOCK_SIZE)
    block[0:4] = MAGIC
    struct.pack_into(">I", block, 0x04, content_offset)
    struct.pack_into(">I", block, 0x08, 3)
    struct.pack_into(">I", block, 0x0C, icon_size)
    struct.pack_into(">I", block, 0x10, banner_size)
    struct.pack_into(">I", block, 0x14, sound_size)

    for i, title in enumerate(titles or []):
        off = 0x1C + i * TITLE_MAX_CHARS * 2
        encoded = title.encode("utf-16-be")[:TITLE_MAX_CHARS * 2]
        block[off:off + len(encoded)] = encoded

    return bytes(block)

class TestIMETRead(unittest.TestCase):

    def setUp(self):
        titles = ["スーパーマリオギャラクシー", "SUPER MARIO GALAXY", "SUPER MARIO GALAXY", "SUPER MARIO GALAXY", "", "", ""]
        raw = b'\x00' * PADDING_SIZE + _make_imet_bytes(titles, icon_size=0xB420, banner_size=0x51620, sound_size=0x26B18)
        self.imet = IMET.read(BytesIO(raw))

    def test_magic_required(self):
        bad = bytearray(b'\x00' * PADDING_SIZE + _make_imet_bytes())
        bad[PADDING_SIZE] = 0xFF
        with self.assertRaises(ValueError):
            IMET.read(BytesIO(bytes(bad)))

    def test_sizes(self):
        self.assertEqual(self.imet.icon_size, 0xB420)
        self.assertEqual(self.imet.banner_size, 0x51620)
        self.assertEqual(self.imet.sound_size, 0x26B18)

    def test_title_english(self):
        self.assertEqual(self.imet.get_title(1), "SUPER MARIO GALAXY")

    def test_title_japanese(self):
        self.assertEqual(self.imet.get_title(0), "スーパーマリオギャラクシー")

    def test_title_empty(self):
        self.assertEqual(self.imet.get_title(4), "")

    def test_title_out_of_range(self):
        self.assertEqual(self.imet.get_title(99), "")


class TestIMETSetTitle(unittest.TestCase):

    def setUp(self):
        raw = b'\x00' * PADDING_SIZE + _make_imet_bytes([""] * TITLE_COUNT)
        self.imet = IMET.read(BytesIO(raw))

    def test_set_and_get(self):
        self.imet.set_title("Test Game", 1)
        self.assertEqual(self.imet.get_title(1), "Test Game")

    def test_set_invalid_language(self):
        with self.assertRaises(ValueError):
            self.imet.set_title("X", TITLE_COUNT)

    def test_set_does_not_affect_other_language(self):
        self.imet.set_title("EN", 1)
        self.assertEqual(self.imet.get_title(0), "")


class TestIMETRoundtrip(unittest.TestCase):

    def test_roundtrip_preserves_titles(self):
        titles = ["日本語タイトル", "English Title", "Deutsch Titel", "Titre Français", "", "", ""]
        raw = b'\x00' * PADDING_SIZE + _make_imet_bytes(titles)
        imet = IMET.read(BytesIO(raw))

        buf = BytesIO()
        imet.write(buf)
        imet2 = IMET.read(BytesIO(buf.getvalue()))

        for i, expected in enumerate(titles):
            self.assertEqual(imet2.get_title(i), expected)

    def test_set_title_roundtrip(self):
        raw = b'\x00' * PADDING_SIZE + _make_imet_bytes([""] * TITLE_COUNT)
        imet = IMET.read(BytesIO(raw))
        imet.set_title("Patched Title", 1)

        buf = BytesIO()
        imet.write(buf)
        imet2 = IMET.read(BytesIO(buf.getvalue()))

        self.assertEqual(imet2.get_title(1), "Patched Title")

    def test_write_output_size(self):
        raw = b'\x00' * PADDING_SIZE + _make_imet_bytes()
        imet = IMET.read(BytesIO(raw))
        buf = BytesIO()
        imet.write(buf)
        self.assertEqual(len(buf.getvalue()), PADDING_SIZE + IMET_BLOCK_SIZE)