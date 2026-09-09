from abc import ABC, abstractmethod
from typing import BinaryIO, ClassVar

from wiithon.binary.align import align
from wiithon.binary.reader import BinaryReader
from wiithon.binary.writer import BinaryWriter

PADDING_STRING = "This is padding data to alignme"

class BDLSection(ABC):
    magic: ClassVar[str]

    @classmethod
    @abstractmethod
    def read(cls, stream: BinaryIO) -> "BDLSection":
        """Read a BDL file from a data stream."""

    @abstractmethod
    def write(self, stream: BinaryIO) -> None:
        """Write a BDL file to a data stream"""

    def read_string_table(self, stream: BinaryIO) -> list[str]:
        reader = BinaryReader(stream)

        table_start = reader.tell()

        string_count = reader.u16()
        reader.skip(2)

        string_offsets = []
        for string_index in range(string_count):
            reader.skip(2) # Hash that we don't care about
            string_offset = reader.u16()
            string_offsets.append(string_offset)

        strings: list[str] = []
        for string_offset in string_offsets:
            reader.seek(table_start + string_offset)

            string = reader.string_until_null('utf-8')
            strings.append(string)

        return strings

    def write_string_table(self, stream: BinaryIO, strings: list[str]) -> None:
        writer = BinaryWriter(stream)

        # Start at the end of the header
        offsets: list[int] = [4 + len(strings) * 4]
        for string in strings:
            offsets.append(offsets[-1] + len(string) + 1)

        def hash(string: str) -> int:
            out = 0
            for char in string.encode():
                out *= 3
                out += char

            return out & 0xFFFF

        writer.u16(len(strings))
        writer.pad(2, b'\xFF')

        for offset, string in zip(offsets, strings):
            writer.u16(hash(string))
            writer.u16(offset)

        for string in strings:
            writer.string(string, add_null_byte = True)

        self.write_padding(writer.stream, 0x20)

    def write_padding(self, stream: BinaryIO, boundary: int) -> None:
        writer = BinaryWriter(stream)

        pad_boundary = align(writer.tell(), boundary)
        pad_size = pad_boundary - writer.tell()
        writer.string(PADDING_STRING[:pad_size])

class RawSection(BDLSection):
    def __init__(self) -> None:
        self.data: bytes = b''

    @classmethod
    def read(cls, stream: BinaryIO) -> "RawSection":
        obj = cls()
        reader = BinaryReader(stream)

        reader.stream.seek(-8, 1)
        obj.magic = reader.string(4)

        section_size = reader.u32()
        obj.data = reader.raw(section_size - 8)

        return obj

    def write(self, stream: BinaryIO) -> None:
        writer = BinaryWriter(stream)
        writer.raw(self.data)
