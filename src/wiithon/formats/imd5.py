from io import BytesIO
from typing import BinaryIO
import hashlib
from wiithon.binary.reader import read_u32, read_string, read_bytes, read_u8
from wiithon.binary.writer import write_u32, write_bytes
from wiithon.exceptions import InvalidFormatError, CorruptedDataError


class IMD5:
    def __init__(self):
        self.magic_word = ""
        self.filesize: int
        self.zeroes: bytes
        self.crypto: bytes

    @staticmethod
    def unwrap(stream: BinaryIO) -> bytes:
        magic_word = read_string(stream, 4)
        if magic_word != "IMD5":
            raise InvalidFormatError("Magic word is not IMD5")

        filesize = read_u32(stream)

        for _ in range(8):
            read_u8(stream)

        md5 = read_bytes(stream, 16)

        payload = read_bytes(stream, filesize)
        hash = hashlib.md5(payload)

        if hash.digest() != md5:
            raise CorruptedDataError("MD5 hash does not match")

        return payload

    @staticmethod
    def wrap(data: bytes) -> bytes:
        dest = BytesIO()
        dest.write(b"IMD5")
        write_u32(dest, len(data))
        write_bytes(dest, b'\x00\x00\x00\x00\x00\x00\x00\x00')

        hash = hashlib.md5(data)
        write_bytes(dest, hash.digest())
        write_bytes(dest, data)
        return dest.getvalue()

