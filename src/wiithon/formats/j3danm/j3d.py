from abc import ABC, abstractmethod
from enum import IntEnum
from typing import BinaryIO, ClassVar

from wiithon.binary.align import align
from wiithon.binary.reader import BinaryReader
from wiithon.binary.writer import BinaryWriter
from wiithon.exceptions import InvalidFormatError

PADDING_STRING = "This is padding data to alignme"
PAD_BYTE = b'\xFF'
PAD_BOUNDARY = 0x20

STRING_ENCODING = "ascii"


class LoopMode(IntEnum):
    ONCE = 0x0
    ONCE_AND_RESET = 0x1
    LOOP = 0x2
    MIRRORED_ONCE = 0x3
    MIRRORED_LOOP = 0x4


class J3DAnmBase(ABC):
    j3d_magic: ClassVar[str] = "J3D1"
    file_magic: ClassVar[str]
    section_count: ClassVar[int]

    @classmethod
    @abstractmethod
    def read(cls, stream: BinaryIO) -> "J3DAnmBase":
        """Read a J3D file from a data stream."""
    

    @abstractmethod
    def write(self, stream: BinaryIO) -> None:
        """Write a J3D file to a data stream."""


    def read_header(self, stream: BinaryIO) -> tuple[int, int]:
        reader = BinaryReader(stream)

        j3d_magic = reader.string(4)
        if j3d_magic != self.j3d_magic:
            raise InvalidFormatError(f"Invalid file magic, {j3d_magic!r} instead of {self.j3d_magic!r}")

        file_magic = reader.string(4)
        if file_magic != self.file_magic:
            raise InvalidFormatError(f"Invalid file magic, {file_magic!r} instead of {self.file_magic!r}")

        file_size = reader.u32()
        section_count = reader.u32()

        reader.skip(0x10)

        return file_size, section_count
    

    def write_header(self, stream: BinaryIO) -> None:
        writer = BinaryWriter(stream)

        writer.string(self.j3d_magic)
        writer.string(self.file_magic)
        writer.u32(0) # Write the file size later
        writer.u32(self.section_count)
        self.pad_byte(writer.stream)


    @staticmethod
    def hash_name(name: str) -> int:
        ret = 0
        for char in name.encode(STRING_ENCODING):
            ret *= 3
            ret += char
        return ret & 0xFFFF


    @staticmethod
    def read_name_table(stream: BinaryIO) -> list[str]:
        reader = BinaryReader(stream)

        table_start = reader.tell()

        name_count = reader.u16()
        reader.skip(2)

        names: list[str] = []
        for name_index in range(name_count):
            reader.seek(table_start + 0x4 + name_index * 0x4)

            reader.skip(2)
            name_offset = reader.u16()

            reader.seek(table_start + name_offset)
            name = reader.string_until_null()
            names.append(name)
        return names


    @staticmethod
    def write_name_table(stream: BinaryIO, names: list[str]) -> None:
        writer = BinaryWriter(stream)

        writer.u16(len(names))
        writer.pad(2, PAD_BYTE)


        name_offset = 4 + len(names) * 4
        for name in names:
            writer.u16(J3DAnmBase.hash_name(name))
            writer.u16(name_offset)

            name_offset += len(name) + 1

        for name in names:
            writer.string(name, add_null_byte=True)

        J3DAnmBase.pad_string(writer.stream)


    @staticmethod
    def pad_string(stream: BinaryIO, boundary = PAD_BOUNDARY) -> None:
        writer = BinaryWriter(stream)

        pad_boundary = align(writer.tell(), boundary)
        pad_size = pad_boundary - writer.tell()

        writer.string(PADDING_STRING[:pad_size])


    @staticmethod
    def pad_byte(stream: BinaryIO, boundary = PAD_BOUNDARY) -> None:
        writer = BinaryWriter(stream)

        pad_boundary = align(writer.tell(), boundary)
        pad_size = pad_boundary - writer.tell()

        writer.pad(pad_size, PAD_BYTE)
