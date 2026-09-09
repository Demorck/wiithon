import hashlib
import struct
import unittest
from io import BytesIO

from wiithon.exceptions import BinaryError, InvalidFormatError
from wiithon.formats.imet import (
    IMET,
    IMET_BLOCK_SIZE,
    IMET_LANGUAGES,
    IMET_MAGIC_WORD,
    IMET_PADDING_SIZE,
    IMET_TITLE_MAX_BYTES,
)

HASH_SIZE = IMET_PADDING_SIZE + IMET_BLOCK_SIZE
MD5_OFFSET = 0x5B0

ICON_SIZE = 0x1000
BANNER_SIZE = 0x2000
SOUND_SIZE = 0x3000

TITLES = {
    "Japanese": "スーパーマリオギャラクシー",
    "English":  "SUPER MARIO GALAXY",
    "French":   "SUPER MARIO GALAXY",
}


def _build_imet(titles: dict[str, str] | None = None, icon_size: int = ICON_SIZE, banner_size: int = BANNER_SIZE,
                sound_size: int = SOUND_SIZE) -> bytes:
    block = bytearray(IMET_BLOCK_SIZE)
    block[0x00:0x04] = IMET_MAGIC_WORD
    struct.pack_into(">I", block, 0x04, HASH_SIZE)
    struct.pack_into(">I", block, 0x08, 0x03)
    struct.pack_into(">III", block, 0x0C, icon_size, banner_size, sound_size)

    for language, title in (TITLES if titles is None else titles).items():
        offset = 0x1C + IMET_LANGUAGES.index(language) * IMET_TITLE_MAX_BYTES
        encoded = title.encode("utf-16-be")
        block[offset:offset + len(encoded)] = encoded

    header = b'\x00' * IMET_PADDING_SIZE + bytes(block)
    block[MD5_OFFSET:MD5_OFFSET + 0x10] = hashlib.md5(header).digest()

    return b'\x00' * IMET_PADDING_SIZE + bytes(block)


def _md5_of(header: bytes) -> bytes:
    zeroed = bytearray(header)
    zeroed[IMET_PADDING_SIZE + MD5_OFFSET:IMET_PADDING_SIZE + MD5_OFFSET + 0x10] = b'\x00' * 0x10
    return hashlib.md5(bytes(zeroed)).digest()


class TestIMETRead(unittest.TestCase):

    def setUp(self):
        self.raw = _build_imet()
        self.imet = IMET.read(BytesIO(self.raw))

    def test_titles(self):
        self.assertEqual(self.imet.titles[IMET_LANGUAGES.index("English")], "SUPER MARIO GALAXY")
        self.assertEqual(self.imet.titles[IMET_LANGUAGES.index("Japanese")], "スーパーマリオギャラクシー")

    def test_unset_language_is_empty(self):
        self.assertEqual(self.imet.titles[IMET_LANGUAGES.index("German")], "")

    def test_sizes(self):
        self.assertEqual(self.imet.icon_size, ICON_SIZE)
        self.assertEqual(self.imet.banner_size, BANNER_SIZE)
        self.assertEqual(self.imet.sound_size, SOUND_SIZE)

    def test_hash_size(self):
        self.assertEqual(self.imet.hash_size, HASH_SIZE)

    def test_stream_is_left_right_after_the_header(self):
        stream = BytesIO(self.raw + b'\xEE' * 4)
        IMET.read(stream)
        self.assertEqual(stream.tell(), HASH_SIZE)

    def test_read_starts_at_the_current_position(self):
        stream = BytesIO(b'\x99' * 0x20 + self.raw)
        stream.seek(0x20)
        imet = IMET.read(stream)
        self.assertEqual(imet.icon_size, ICON_SIZE)

    def test_get_title_defaults_to_english(self):
        self.assertEqual(self.imet.get_title(), "SUPER MARIO GALAXY")

    def test_get_title_out_of_range(self):
        self.assertEqual(self.imet.get_title(42), "")

    def test_bad_magic_raises(self):
        broken = bytearray(self.raw)
        broken[IMET_PADDING_SIZE:IMET_PADDING_SIZE + 4] = b"IMD5"
        with self.assertRaises(InvalidFormatError):
            IMET.read(BytesIO(bytes(broken)))

    def test_truncated_raises(self):
        with self.assertRaises(BinaryError):
            IMET.read(BytesIO(self.raw[:0x200]))


class TestIMETWrite(unittest.TestCase):

    def setUp(self):
        self.raw = _build_imet()
        self.imet = IMET.read(BytesIO(self.raw))

    def _write(self) -> bytes:
        stream = BytesIO()
        self.imet.write(stream)
        return stream.getvalue()

    def test_roundtrip_is_byte_identical(self):
        self.assertEqual(self._write(), self.raw)

    def test_leading_padding_stays_empty(self):
        self.assertEqual(self._write()[:IMET_PADDING_SIZE], b'\x00' * IMET_PADDING_SIZE)

    def test_layout(self):
        out = self._write()
        self.assertEqual(len(out), HASH_SIZE)
        self.assertEqual(out[IMET_PADDING_SIZE:IMET_PADDING_SIZE + 4], IMET_MAGIC_WORD)

    def test_set_title_is_written(self):
        self.imet.set_title("FEUR", "English")
        again = IMET.read(BytesIO(self._write()))
        self.assertEqual(again.get_title(), "FEUR")

    def test_shorter_title_clears_the_old_one(self):
        self.imet.set_title("AB", "English")
        again = IMET.read(BytesIO(self._write()))
        self.assertEqual(again.get_title(), "AB")

    def test_other_languages_are_kept(self):
        self.imet.set_title("FEUR", "English")
        again = IMET.read(BytesIO(self._write()))
        self.assertEqual(again.titles[IMET_LANGUAGES.index("French")], "SUPER MARIO GALAXY")
        self.assertEqual(again.titles[IMET_LANGUAGES.index("Japanese")], "スーパーマリオギャラクシー")

    def test_too_long_title_is_truncated(self):
        self.imet.set_title("Z" * 60, "English")
        again = IMET.read(BytesIO(self._write()))
        self.assertEqual(again.get_title(), "Z" * (IMET_TITLE_MAX_BYTES // 2))

    def test_sizes_are_written(self):
        self.imet.icon_size = 0x11
        self.imet.banner_size = 0x22
        self.imet.sound_size = 0x33
        again = IMET.read(BytesIO(self._write()))
        self.assertEqual((again.icon_size, again.banner_size, again.sound_size), (0x11, 0x22, 0x33))

    def test_md5_is_recomputed(self):
        self.imet.set_title("FEUR", "English")
        out = self._write()
        stored = out[IMET_PADDING_SIZE + MD5_OFFSET:IMET_PADDING_SIZE + MD5_OFFSET + 0x10]
        self.assertEqual(stored, _md5_of(out))
        self.assertNotEqual(stored, self.raw[IMET_PADDING_SIZE + MD5_OFFSET:IMET_PADDING_SIZE + MD5_OFFSET + 0x10])

    def test_unknown_language_raises(self):
        with self.assertRaises(ValueError):
            self.imet.set_title("FEUR", "\"Breton\"")


if __name__ == "__main__":
    unittest.main()