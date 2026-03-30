from io import BytesIO
from typing import BinaryIO

from helpers.Utils import read_string, read_u32, read_u8


class Yaz0:
    def __init__(self):
        self.size: int = 0
        self.magic_word: str = ""
        self.data: bytes = b""

    @classmethod
    def read(cls, stream: BinaryIO) -> "Yaz0":
        obj = cls()

        obj.magic_word = read_string(stream, 0x04)
        if obj.magic_word != "Yaz0":
            raise ValueError("Trying to read a non-yaz0 file with the yaz0 struct")

        obj.size = read_u32(stream)
        stream.read(0x8)

        compressed_data: bytes = stream.read()
        obj.data = Yaz0.uncompress(compressed_data, obj.size)

        return obj

    @staticmethod
    def uncompress(compressed_data: bytes, size: int) -> bytes:
        dest_buffer = bytearray()
        src_buffer = BytesIO(compressed_data)

        while len(dest_buffer) < size:
            group_header = read_u8(src_buffer)
            for i in range(8):
                if len(dest_buffer) >= size:
                    break

                if group_header & (0x80 >> i):
                    dest_buffer.append(read_u8(src_buffer))
                else:
                    byte1 = read_u8(src_buffer)
                    byte2 = read_u8(src_buffer)

                    distance = ((byte1 & 0xF) << 8) | byte2
                    copy_src = len(dest_buffer) - distance - 1
                    
                    number_to_copy = byte1 >> 4
                    if number_to_copy == 0:
                        number_to_copy = read_u8(src_buffer) + 0x12
                    else:
                        number_to_copy += 2

                    if number_to_copy < 3 or number_to_copy > 0x111:
                        raise ValueError("Something happens when decompressing yaz0 file")

                    for j in range(number_to_copy):
                        dest_buffer.append(dest_buffer[copy_src])
                        copy_src += 1

        return bytes(dest_buffer)
