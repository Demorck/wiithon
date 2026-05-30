import hashlib
import struct
from typing import BinaryIO

from wiithon.helpers.Constants import (
    IMET_TITLE_COUNT, IMET_PADDING_SIZE, IMET_BLOCK_SIZE, \
    IMET_MAGIC_WORD, IMET_TITLE_MAX_BYTES, IMET_LANGUAGES
)


class IMET:
    def __init__(self):
        self.icon_size: int = 0
        self.banner_size: int = 0
        self.sound_size: int = 0
        self.titles: list[str] = [""] * IMET_TITLE_COUNT
        self._content_offset: int = 0
        self._raw_block: bytes = b""

    @classmethod
    def read(cls, stream: BinaryIO) -> "IMET":
        obj = cls()
        start = stream.tell()

        stream.seek(start + IMET_PADDING_SIZE)
        obj._raw_block = stream.read(IMET_BLOCK_SIZE)

        if len(obj._raw_block) < IMET_BLOCK_SIZE or obj._raw_block[:4] != IMET_MAGIC_WORD:
            raise ValueError(f"Invalid IMET magic: {obj._raw_block[:4]!r}")

        obj._content_offset = struct.unpack_from(">I", obj._raw_block, 0x04)[0]
        obj.icon_size        = struct.unpack_from(">I", obj._raw_block, 0x0C)[0]
        obj.banner_size      = struct.unpack_from(">I", obj._raw_block, 0x10)[0]
        obj.sound_size       = struct.unpack_from(">I", obj._raw_block, 0x14)[0]

        for i in range(IMET_TITLE_COUNT):
            off = 0x1C + i * IMET_TITLE_MAX_BYTES
            raw = obj._raw_block[off:off + IMET_TITLE_MAX_BYTES]
            end = 0
            while end < IMET_TITLE_MAX_BYTES - 1:
                if raw[end] == 0 and raw[end + 1] == 0:
                    break
                end += 2
            obj.titles[i] = raw[:end].decode("utf-16-be", errors="replace")

        return obj

    def get_title(self, language: int = 1) -> str:
        if 0 <= language < len(self.titles):
            return self.titles[language]
        return ""

    def set_title(self, title: str, language: str = "English") -> None:
        if language in IMET_LANGUAGES:
            err_str = ", ".join(IMET_LANGUAGES)
            raise ValueError(f"language must be in one of these: {err_str}")

        idx = IMET_LANGUAGES.index(language)
        self.titles[idx] = title

    def write(self, stream: BinaryIO) -> None:
        stream.write(b'\x00' * IMET_PADDING_SIZE)

        buf = bytearray(self._raw_block)
        for i in range(IMET_TITLE_COUNT):
            off = 0x1C + i * IMET_TITLE_MAX_BYTES
            encoded = self.titles[i].encode("utf-16-be")[:IMET_TITLE_MAX_BYTES]
            buf[off:off + IMET_TITLE_MAX_BYTES] = b'\x00' * IMET_TITLE_MAX_BYTES
            buf[off:off + len(encoded)] = encoded

        buf[0x5B0:0x5C0] = b'\x00' * 16
        digest = hashlib.md5(buf[:0x5B0]).digest()
        buf[0x5B0:0x5C0] = digest

        stream.write(bytes(buf))

    def __repr__(self) -> str:
        lines = [f"IMET  icon={self.icon_size:#x}  banner={self.banner_size:#x}  sound={self.sound_size:#x}"]
        for i, lang in enumerate(IMET_LANGUAGES):
            if self.titles[i]:
                lines.append(f"  {lang:10s}: {self.titles[i]}")
        return "\n".join(lines)