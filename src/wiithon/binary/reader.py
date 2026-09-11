"""
A reader that can read from a stream or bytes.

Used by everything in wiithon since it checks the validity of readed bytes
"""
import struct
from io import BytesIO
from typing import BinaryIO

from wiithon.binary.common import STRING_FORMAT
from wiithon.exceptions import BinaryError


class BinaryReader:
    """
    A reader that can read from a stream or bytes.

    Bytes are converted to a stream
    """
    def __init__(self, stream: BinaryIO, encoding: str = STRING_FORMAT) -> None:
        #: Stream to read for operations
        self.stream = stream

        #: Encoding used by default for reading string
        self.encoding = encoding

    @classmethod
    def from_bytes(cls, data: bytes) -> "BinaryReader":
        """
        Converted bytes to stream so BinaryReader can read it.

        Args:
            data: Bytes to convert.

        Returns:
            A BinaryReader with a stream to read of
        """
        stream = BytesIO(data)
        return cls(stream)

    def seek(self, offset: int) -> None:
        """
        Change the stream's cursor position to a given offset

        Args:
            offset: The new stream's cursor
        """
        self.stream.seek(offset)

    def tell(self) -> int:
        """
        Get the current stream cursor position

        Returns:
            The current stream cursor position within the stream
        """
        return self.stream.tell()

    def skip(self, count: int) -> None:
        """
        Skip a given number of bytes. It reads this number and returns nothing

        Args:
            count: The number of bytes to skip

        """
        self.stream.read(count)

    def _read_number(self, size: int, unpack_fmt: str) -> int:
        """
        Reads a number from the stream from a given size at the current stream position

        Args:
            size: The number of bytes to read
            unpack_fmt: The format used by the unpack function

        Raises:
            BinaryError: If the len read is different from the given size

        Returns:
            The number read from the stream
        """
        data = self.stream.read(size)
        if len(data) != size:
            raise BinaryError(
                f"Tried to read {size} bytes at offset {self.stream.tell() - len(data)}, "
                f"got {len(data)}."
            )
        return struct.unpack(unpack_fmt, data)[0]

    # Numbers
    def u8(self) -> int:
        """
        Read a single unsigned byte from the stream in big-endian at the current stream position.
        The cursor is placed after the read byte

        Returns:
            The byte read from the stream
        """
        return self._read_number(1,'>B')

    def u16(self) -> int:
        """
        Read two unsigned bytes from the stream in big-endian at the current stream position.
        The cursor is placed after the read byte

        Returns:
            Integer reads from the stream
        """
        return self._read_number(2,'>H')

    def u32(self) -> int:
        """
        Read four unsigned bytes from the stream in big-endian at the current stream position.
        The cursor is placed after the read byte

        Returns:
            Integer reads from the stream
        """
        return self._read_number(4,'>I')

    def u64(self) -> int:
        """
        Read eight unsigned bytes from the stream in big-endian at the current stream position.
        The cursor is placed after the read byte

        Returns:
            The  from the stream
        """
        return self._read_number(8,'>Q')

    def s8(self) -> int:
        """
        Read a single signed byte from the stream in big-endian at the current stream position.
        The cursor is placed after the read byte

        Returns:
            The number read from the stream
        """
        return self._read_number(1, '>b')

    def s16(self) -> int:
        """
        Read two signed bytes from the stream in big-endian at the current stream position.
        The cursor is placed after the read byte

        Returns:
            Integer reads from the stream
        """
        return self._read_number(2, '>h')

    def s32(self) -> int:
        """
        Read four signed bytes from the stream in big-endian at the current stream position.
        The cursor is placed after the read byte

        Returns:
            Integer reads from the stream
        """
        return self._read_number(4, '>i')

    def s64(self) -> int:
        """
        Read eight signed bytes from the stream in big-endian at the current stream position.
        The cursor is placed after the read byte

        Returns:
            Integer reads from the stream
        """
        return self._read_number(8, '>q')

    def float(self) -> float:
        """
        Read a float number from the stream in big-endian at the current stream position.
        The cursor is placed after the read byte

        Returns:
            Float reads from the stream
        """
        return self._read_number(4, '>f')

    def u32_shifted(self) -> int:
        """
        Reads an unsigned 32 bits number then left shifted 2 times.

        Some file formats use this.

        Returns:
            The number left shifted 2 times from the stream
        """
        return self.u32() << 2

    def u32_le(self) -> int:
        return self._read_number(4, '<I')

    def raw(self, size: int = -1) -> bytes:
        """
        Read ``size`` raw bytes from the stream.

        Args:
            size: The number of bytes to read

        Returns:
            Number of byte read from the stream
        """
        data = self.stream.read(size)
        if 0 <= size != len(data):
            raise BinaryError(f"Tried to read {size} bytes, got {len(data)}.")
        return data

    def list_u32(self, size: int) -> list[int]:
        """
        Read a list of unsigned 32 bits numbers one after the other

        Args:
            size: How many numbers to read

        Returns:
            A list of unsigned 32 bits numbers
        """
        result_list: list[int] = [self.u32() for _ in range(size)]

        return result_list

    # Strings
    def string(self, size: int, encoding: str | None = None) -> str:
        """
        Read a string from the stream with a certain size and a certain encoding

        Args:
            size: The number of bytes to read
            encoding: The encoding to use

        Returns:
            The string decoded
        """
        return self.raw(size).split(b'\x00')[0].decode(encoding or self.encoding)

    def string_until_null(self, encoding: str | None = None) -> str:
        """
        Read a string from the stream until a null byte (``\x00``) is found

        Args:
            encoding: The encoding to use

        Returns:
            The string decoded
        """
        encoding = encoding or self.encoding
        null_byte = '\0'.encode(encoding)
        chars = bytearray()
        while True:
            byte = self.stream.read(len(null_byte))
            if byte == null_byte or not byte:
                break
            chars += byte

        return chars.decode(encoding)