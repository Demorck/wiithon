from typing import BinaryIO
import struct

from wiithon.binary.reader import read_u32

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

    def __repr__(self):
        lines = []
        for i in range(7):
            if self.text_length[i] > 0:
                end = self.text_starts[i] + self.text_length[i]
                lines.append(f"  text[{i}]: {self.text_starts[i]:08X} - {end:08X} - Off: {self.text_offset[i]:08X}  (size: {self.text_length[i]:08X})")
            else:
                lines.append(f"  text[{i}]: (free)")
        for i in range(11):
            if self.data_length[i] > 0:
                end = self.data_starts[i] + self.data_length[i]
                lines.append(f"  data[{i}]: {self.data_starts[i]:08X} - {end:08X} - Off: {self.data_offset[i]:08X}  (size: {self.data_length[i]:08X})")
            else:
                lines.append(f"  data[{i}]: (free)")


        bss_end = self.bss_start + self.bss_size
        return (
                f"entry:  {self.entry_point:08X}\n"
                f"bss:    {self.bss_start:08X} — {bss_end:08X}  (size: {self.bss_size:08X})\n"
                f"sections:\n" + "\n".join(lines)
        )

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