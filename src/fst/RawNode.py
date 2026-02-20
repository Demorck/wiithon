from typing import BinaryIO
import struct

class RawFSTNode:
    """
    On-disk FST entry (12 bytes)
    This is the raw binary format stored on the Wii disc
    """
    SIZE: int = 12
    def __init__(self) -> None:
        self.is_directory: bool = False
        self.name_offset: int = 0
        self.data_offset: int = 0
        self.length: int = 0

    @classmethod
    def read(cls, stream: BinaryIO) -> "RawFSTNode":
        """
        Read a 12-byte FST entry from a binary stream.
        :param stream:
        :return:
        """
        obj = cls()
        data = stream.read(12)

        # Byte 0: is_directory flag
        obj.is_directory = data[0] != 0

        # Bytes 1-3: name_offset (u24)
        obj.name_offset = (data[1] << 16) | (data[2] << 8) | data[3]
        # Bytes 4-7: data_offset (u32)
        obj.data_offset = struct.unpack('>I', data[4:8])[0]
        # Bytes 8-11: length (u32)
        obj.length = struct.unpack('>I', data[8:12])[0]

        return obj

    def write(self, stream: BinaryIO) -> None:
        """Write this entry as 12 bytes to a binary stream.
        :param stream:
        """

        # Byte 0: is_directory flag
        stream.write(struct.pack('>B', 1 if self.is_directory else 0))

        # Bytes 1-3: name_offset as u24 big-endian
        stream.write(bytes([
            (self.name_offset >> 16) & 0xFF,
            (self.name_offset >> 8) & 0xFF,
            self.name_offset & 0xFF,
        ]))

        # Bytes 4-11: data_offset + length
        stream.write(struct.pack('>II', self.data_offset, self.length))