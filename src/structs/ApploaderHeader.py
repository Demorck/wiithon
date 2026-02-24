from typing import BinaryIO
from helpers.Utils import read_u32
import struct

class ApploaderHeader:
    """

    """
    def __init__(self):
        self.size1 = 0
        self.size2 = 0

    @classmethod
    def read(cls, stream: BinaryIO) -> 'ApploaderHeader':
        obj = cls()

        stream.read(0x14)
        obj.size1 = read_u32(stream)
        obj.size2 = read_u32(stream)

        return obj

    def write(self, stream: BinaryIO) -> None:
        stream.write(b'\x00' * 0x14)
        stream.write(struct.pack('>I', self.size1))
        stream.write(struct.pack('>I', self.size2))
