"""
Write numbers, strings and raw bytes into a binary stream

This module exposes :class:`BinaryWriter`, the counterpart of :class:`~wiithon.binary.reader.BinaryReader`
Everything is written in big-endian since it is what the Wii uses
"""
import struct
from typing import BinaryIO

from wiithon.binary.common import STRING_FORMAT
from wiithon.exceptions import BinaryError


class BinaryWriter:
    """
    A writer that appends structured values to a stream

    The writer never owns the stream, it only writes in it, so closing it is up to the caller
    Contrary to the reader there is no ``from_bytes`` helper, wrap a :class:`io.BytesIO` yourself and read it
    back with ``getvalue()``

    Example:
        >>> buf = BytesIO()
        >>> writer = BinaryWriter(buf)
        >>> writer.u32(0x5D1C9EA3)
        >>> writer.string("GAME", 0x10)
        >>> data = buf.getvalue()
    """
    def __init__(self, stream: BinaryIO, encoding: str = STRING_FORMAT) -> None:
        #: Stream to write for operations
        self.stream = stream

        #: Encoding used by default for writing
        self.encoding = encoding

    def seek(self, offset: int) -> None:
        """
        Change the stream cursor position to a given offset

        Args:
            offset: The new stream cursor

        Note:
            Seeking past the end of the stream does not grow it, the gap is filled only when you write there
        """
        self.stream.seek(offset)

    def tell(self) -> int:
        """
        Get the current stream cursor position

        Returns:
            The current stream cursor position within the stream
        """
        return self.stream.tell()

    def pad(self, count: int, byte: bytes = b'\x00') -> None:
        """
        Write a filler of ``count`` bytes to the stream of the same byte, used to align structure
        on a boundary

        Args:
            count: How many times ``byte`` is written
            byte: The filler byte. Default is null byte

        Note:
            ``count`` is the number of repetitions, not a number of bytes.
        """
        self.stream.write(count * byte)

    def size(self) -> int:
        """
        Get the total size of the stream

        The cursor is moved to the end to measure the stream then put back where it was.

        Returns:
            The size of the whole stream in bytes, not the number of bytes written
        """
        current_offset = self.tell()
        size = self.stream.seek(0, 2)
        self.seek(current_offset)
        return size

    def _write_number(self, number: int | float, pack_fmt: str) -> None:
        """
        Pack a number and write it at the current stream position

        Args:
            number: The number to write
            pack_fmt: The format used by the pack function
        """
        data = struct.pack(pack_fmt, number)
        self.stream.write(data)

    # Numbers
    def u8(self, data: int) -> None:
        """
        Write a single unsigned byte to the stream in big-endian at the current stream position
        The cursor is placed after the written byte

        Args:
            data: The number to write, from 0 to 255
        """
        self._write_number(data,'>B')

    def u16(self, data: int) -> None:
        """
       Write two unsigned bytes to the stream in big-endian at the current stream position
       The cursor is placed after the written bytes

       Args:
           data: The number to write, from 0 to 65535
       """
        self._write_number(data,'>H')

    def u32(self, data: int) -> None:
        """
        Write four unsigned bytes to the stream in big-endian at the current stream position
        The cursor is placed after the written bytes

        Args:
            data: The number to write, from 0 to 4294967295
        """
        self._write_number(data,'>I')

    def u64(self, data: int) -> None:
        """
        Write eight unsigned bytes to the stream in big-endian at the current stream position
        The cursor is placed after the written bytes

        Args:
            data: The number to write, from 0 to 18446744073709551615
        """
        self._write_number(data,'>Q')

    def s8(self, data: int) -> None:
        """
        Write a single signed byte to the stream in big-endian at the current stream position
        The cursor is placed after the written byte

        Args:
            data: The number to write, from -128 to 127
        """
        self._write_number(data, '>b')

    def s16(self, data: int) -> None:
        """
        Write two signed bytes to the stream in big-endian at the current stream position
        The cursor is placed after the written bytes

        Args:
            data: The number to write, from -32768 to 32767
        """
        self._write_number(data, '>h')

    def s32(self, data: int) -> None:
        """
        Write four signed bytes to the stream in big-endian at the current stream position
        The cursor is placed after the written bytes

        Args:
            data: The number to write, from -2147483648 to 2147483647
        """
        self._write_number(data, '>i')

    def s64(self, data: int) -> None:
        """
        Write eight signed bytes to the stream in big-endian at the current stream position
        The cursor is placed after the written bytes

        Args:
            data: The number to write, from -9223372036854775808 to 9223372036854775807
        """
        self._write_number(data, '>q')

    def float(self, data: float) -> None:
        """
        Write a 32 bits float to the stream in big-endian at the current stream position
        The cursor is placed after the written bytes

        Args:
            data: The number to write
        """
        self._write_number(data, '>f')


    def list_u32(self, numbers: list[int]) -> None:
        """
        Write a list of unsigned 32 bits numbers one after the other

        Args:
            numbers: The numbers to write, in the order they are stored

        Note:
            No count is written before the list. If the format needs one, write it yourself
        """
        for num in numbers:
            self.u32(num)

    def u32_shifted(self, data: int) -> None:
        """
        Right shift a number 2 times then write it as an unsigned 32 bits number

        This is the inverse of :meth:`~wiithon.binary.reader.BinaryReader.u32_shifted`, for the formats that
        store offsets divided by 4

        Args:
            data: The real value, before the shift

        Warning:
            The two low bits are lost.
        """
        self.u32(data >> 2)

    def u32_le(self, data: int) -> None:
        """
        Write four unsigned bytes to the stream in little-endian at the current stream position

        Args:
            data: The number to write

        Note:
            Almost everything on a Wii disc is big-endian. This is only for the few structures that are not
        """
        self._write_number(data, '<I')

    def raw(self, data: bytes) -> None:
        """
        Write bytes to the stream as they are, without any conversion

        Args:
            data: The bytes to write
        """
        self.stream.write(data)


    def string(self, value: str, size: int | None = None, padding: bytes = b'\x00',
               encoding: str | None = None, *, add_null_byte: bool = False) -> None:
        """
        Write a string in a field of a fixed size, padded if it is too short

        Args:
            value: The string to write
            size: The size of the field in bytes. Defaults to the encoded length of ``value``, which writes it
                without any padding
            padding: The byte used to fill the end of the field
            encoding: The encoding to use. Defaults to the encoding of the writer
            add_null_byte: Write an extra null byte after the field, for the formats that store strings one
                after the other in a string table

        Raises:
            BinaryError: If the encoded string is longer than ``size``

        Note:
            ``size`` counts encoded bytes, not characters. A japanese string in ``shift_jis`` takes more room
            than its length suggests

        Warning:
            With ``add_null_byte`` the field takes ``size + 1`` bytes, the null byte is not counted inside
        """
        encoded = value.encode(encoding or self.encoding)
        if size is None:
            size = len(encoded)

        if len(encoded) > size:
            raise BinaryError(
                f"String {value!r} encodes to {len(encoded)} bytes, "
                f"which does not fit in a {size} byte field"
            )

        self.raw(encoded + padding * (size - len(encoded)))
        if add_null_byte:
            self.raw(b'\x00')