"""
One content entry of a Title Metadata block

A TMD ends with a list of these, one per content the title is made of. This module exposes :class:`TMDContent`,
which is read and written by :class:`~wiithon.disc.structs.tmd.TMD` and is not meant to be built alone

On a disc the list holds a single entry, index 0, that stands for the whole encrypted partition data

Layout, 0x24 bytes::

    Offset  Size    Field
    0x00    0x04    Content ID
    0x04    0x02    Index
    0x06    0x02    Type (0x0001: Normal, 0x4001: DLC, 0x8001: Shared)
    0x08    0x08    Size
    0x10    0x14    SHA-1 hash

References:
    https://wiibrew.org/wiki/Title_metadata
"""
from typing import BinaryIO

from wiithon.binary.reader import BinaryReader
from wiithon.binary.writer import BinaryWriter

class TMDContent:
    """
    A single content descriptor of a TMD

    The Wii uses this to know the size of a content and to check it against its hash before booting it

    Note:
        Nothing is validated at read time.
    """
    def __init__(self) -> None:
        #: Unique content identifier
        self.id: int = 0

        #: Position of the content list
        self.index: int = 0

        #: Content type. ``0x0001`` for normal, ``0x4001`` for DLC and ``0x8001`` for shared
        self.content_type: int = 0

        #: Content size in bytes
        self.size: int = 0

        #: SHA1 of the content
        self.hash: bytes = b'\x00' * 0x14


    @classmethod
    def read(cls, stream: BinaryIO) -> 'TMDContent':
        """
        Read and parse a content entry from a binary stream

        Args:
            stream: Binary IO stream

        Returns:
            The parsed entry
        """
        obj = cls()
        reader = BinaryReader(stream)

        obj.id              = reader.u32()
        obj.index           = reader.u16()
        obj.content_type    = reader.u16()
        obj.size            = reader.u64()
        obj.hash            = reader.raw(0x14)

        return obj

    def write(self, stream: BinaryIO) -> None:
        """
        Write the content entry to a binary stream at the current position

        Args:
            stream: Binary IO stream

        Note:
            :attr:`size` and :attr:`hash` are written as they are, nothing is recomputed. When building a disc
            they are patched afterwards on the serialised TMD by
            :func:`~wiithon.builder.disc_builder.fakesign_tmd`
        """
        writer = BinaryWriter(stream)

        writer.u32(self.id)
        writer.u16(self.index)
        writer.u16(self.content_type)
        writer.u64(self.size)
        writer.raw(self.hash)