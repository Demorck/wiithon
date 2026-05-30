import struct
import unittest
from io import BytesIO

from wiithon.file_helper.bnr import BNR
from wiithon.structs.IMET import MAGIC, PADDING_SIZE, IMET_BLOCK_SIZE, TITLE_MAX_CHARS


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


def _make_bnr_bytes(titles: list[str] | None = None, inner: bytes = b"INNER") -> bytes:
    buf = BytesIO()
    buf.write(b'\x00' * PADDING_SIZE)
    buf.write(_make_imet_bytes(titles))
    buf.write(inner)
    return buf.getvalue()


class TestBNRRead(unittest.TestCase):

    def test_title_property(self):
        raw = _make_bnr_bytes(["JA", "EN Game", "DE", "FR", "", "", ""])
        bnr = BNR.read(BytesIO(raw))
        self.assertEqual(bnr.title, "EN Game")

    def test_inner_data_preserved(self):
        inner = b"FAKEU8DATA"
        raw = _make_bnr_bytes(inner=inner)
        bnr = BNR.read(BytesIO(raw))
        self.assertEqual(bnr._inner_data, inner)

    def test_roundtrip(self):
        inner = b"FAKEU8DATA"
        titles = ["", "My Game", "", "", "", "", ""]
        raw = _make_bnr_bytes(titles=titles, inner=inner)
        bnr = BNR.read(BytesIO(raw))

        buf = BytesIO()
        bnr.write(buf)
        bnr2 = BNR.read(BytesIO(buf.getvalue()))

        self.assertEqual(bnr2.title, "My Game")
        self.assertEqual(bnr2._inner_data, inner)
