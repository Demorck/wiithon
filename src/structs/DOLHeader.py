from typing import BinaryIO
import struct

from helpers.Utils import read_u32


class DOLHeader:
    """
    https://wiibrew.org/wiki/DOL
    """
    def __init__(self):
        self.text_offset: list[int] = []
        self.data_offset: list[int] = []
        self.text_starts: list[int] = []
        self.data_starts: list[int] = []
        self.text_length: list[int] = []
        self.data_length: list[int] = []
        self.bss_start: int = 0
        self.bss_size: int = 0
        self.entry_point: int = 0

    @classmethod
    def read(cls, stream: BinaryIO) -> "DOLHeader":
        """

        :param stream:
        :return:
        """

        obj = cls()

        obj.text_offset = list(struct.unpack('>7I', stream.read(7 * 4)))
        obj.data_offset = list(struct.unpack('>11I', stream.read(11 * 4)))
        obj.text_starts = list(struct.unpack('>7I', stream.read(7 * 4)))
        obj.data_starts = list(struct.unpack('>11I', stream.read(11 * 4)))
        obj.text_length = list(struct.unpack('>7I', stream.read(7 * 4)))
        obj.data_length = list(struct.unpack('>11I', stream.read(11 * 4)))
        obj.bss_start = read_u32(stream)
        obj.bss_size = read_u32(stream)
        obj.entry_point = read_u32(stream)
        stream.read(0x1C)

        return obj

    def write(self, stream: BinaryIO) -> None:
        """

        :param stream:
        :return:
        """
        stream.write(struct.pack('>7I', *self.text_offset))
        stream.write(struct.pack('>11I', *self.data_offset))
        stream.write(struct.pack('>7I', *self.text_starts))
        stream.write(struct.pack('>11I', *self.data_starts))
        stream.write(struct.pack('>7I', *self.text_length))
        stream.write(struct.pack('>11I', *self.data_length))
        stream.write(struct.pack('>I', self.bss_start))
        stream.write(struct.pack('>I', self.bss_size))
        stream.write(struct.pack('>I', self.entry_point))
        stream.write(b'\x00' * 0x1C)