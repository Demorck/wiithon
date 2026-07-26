from io import BytesIO
from typing import BinaryIO

from wiithon.binary.Utils import read_string, read_u8, read_u16, write_ndata, read_ndata

_buffer_size = 18
_window_size = 4095

class Lz77:

    def __init__(self) -> None:
        self.magic_word = ""
        self.size = 0
        self.compression_method = 0
        self.data: bytes = b''

    @classmethod
    def read(cls, stream: BinaryIO) -> "Lz77":
        obj = cls()

        obj.magic_word = read_string(stream, 0x04)
        if obj.magic_word != "LZ77":
            raise ValueError("Trying to read a non-lz77 file with the lz77 struct")

        header = read_ndata(stream, 4, unpack_fmt='<I')

        obj.compression_method = header & 0xFF
        obj.size = header >> 8

        compressed_data: bytes = stream.read()
        obj.data = Lz77.uncompress(compressed_data, obj.size)

        return obj


    @staticmethod
    def uncompress(compressed_data: bytes, size: int) -> bytes:
        dest_buffer = bytearray()
        src_buffer = BytesIO(compressed_data)

        while len(dest_buffer) < size:
            flags = read_u8(src_buffer)

            for _ in range(8):
                if flags & 0x80: # 0x80 = 1000 000
                    reference = read_u16(src_buffer)
                    length = 3 + ((reference >> 12) & 0xF)
                    offset = reference & 0xFFF
                    pointer = len(dest_buffer) - offset - 1
                    for _ in range(length):
                        dest_buffer.append(dest_buffer[pointer])
                        pointer += 1
                        if len(dest_buffer) >= size:
                            break
                else:
                    data = read_u8(src_buffer)
                    dest_buffer.append(data)

                flags <<= 1
                if len(dest_buffer) >= size:
                    break

        return bytes(dest_buffer)


    def write(self, stream: BinaryIO) -> None:
        self.size = len(self.data)

        stream.write(self.magic_word.encode('ascii'))
        header = (self.size << 8) | self.compression_method
        write_ndata(stream, header, pack_fmt='<I')
        stream.write(Lz77.compress(self.data))

    @staticmethod
    def compress(uncompressed_data: bytes) -> bytes:
        size = len(uncompressed_data)
        dest_buffer = bytearray()

        counter = 0
        flags = 0
        byte_list = bytearray()

        pointer = 0
        while pointer < size:
            match = Lz77._find_longest_match(uncompressed_data, pointer, _buffer_size, _window_size)

            flags <<= 1
            if match:
                (distance, length) = match
                flags |= 1
                reference = (length - 3) << 12
                reference |= distance - 1
                byte_list.append((reference >> 8 * 1) & 0xFF)
                byte_list.append(reference & 0xFF)
                pointer += length
            else:
                flags |= 0
                byte_list.extend(uncompressed_data[pointer:pointer + 1])
                pointer += 1

            counter += 1

            if counter == 8:
                counter = 0
                dest_buffer.append(flags)
                dest_buffer.extend(byte_list)
                byte_list = bytearray()
                flags = 0

        if len(byte_list) > 0:
            dest_buffer.append(flags << (8 - counter))
            dest_buffer.extend(byte_list)

        return bytes(dest_buffer)

    @staticmethod
    def _find_longest_match(data, current_position, buffer_size, window_size):
        cp = current_position
        if cp + 3 > len(data):
            return None

        max_len = min(buffer_size, len(data) - cp)
        prefix = data[cp:cp + 3]
        start = max(0, cp - window_size)
        best = None
        j = data.find(prefix, start, cp + 2)

        while j != -1:
            length = 3

            while length < max_len and data[j + length] == data[cp + length]:
                length += 1

            if best is None or length > best[1]:
                best = (cp - j, length)
                if length == max_len:
                    break

            j = data.find(prefix, j + 1, cp + 2)

        return best