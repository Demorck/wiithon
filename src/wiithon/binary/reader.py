import struct
from typing import BinaryIO
from typing import Any

from wiithon.binary.common import STRING_FORMAT
from wiithon.exceptions import BinaryError


###########################
####### READ UTILS ########
###########################

def read_ndata(stream: BinaryIO, size: int = -1, offset: int = None, unpack_fmt: str = None) -> bytes | Any:
    """
    Read n size data and converts it to the expected data type/size.

    Args:
        stream (BinaryIO): input stream
        offset (int): Offset within the steam to read.
        size (int): If specified (and > 0), does a comparison with the remaining bytes of a stream to verify byte length is available.
        unpack_fmt (str): If specified, unpacks the bytes into a specific output type.
    
    Returns:
        Any: an output type specified by the unpack format. Defaults to bytes if unspecified.
    """
    if size is None:
        size = -1

    if offset is not None:
        if size > 0:
            data_length = stream.seek(0, 2)
            if offset + size > data_length:
                raise BinaryError(f"Offset {offset} + Length {size} ({offset + size}) is longer than the data size {data_length}.")
        stream.seek(offset)

    if unpack_fmt is not None:
        return struct.unpack(unpack_fmt, stream.read(size))[0]
    return stream.read(size)

def read_u64(stream: BinaryIO, offset: int = None) -> int:
    """
    Read a 64-bit unsigned big-endian integer from a stream

    Args:
        stream (BinaryIO): input stream
        offset (int): Offset within the steam to read.
    
    Returns:
        int: 64-bit unsigned integer
    """
    return read_ndata(stream, 8, offset, '>Q')

def read_u32(stream: BinaryIO, offset: int = None) -> int:
    """
    Read a 32-bit unsigned big-endian integer from a stream

    Args:
        stream (BinaryIO): input stream
        offset (int): Offset within the steam to read.
    
    Returns:
        int:32-bit unsigned integer
    """
    return read_ndata(stream, 4, offset, '>I')

def read_u32_shifted(stream: BinaryIO, offset: int = None) -> int:
    """
    Read an u32 and left-shift it by 2 bits (x4)

    Args:
        stream (BinaryIO): input stream
        offset (int): Offset within the steam to read.
    
    Returns:
        int:64-bit unsigned integer
    """
    return read_u32(stream, offset) << 2

def read_u16(stream: BinaryIO, offset: int = None) -> int:
    """
    Read a 16-bit unsigned big-endian integer from a stream
    
    Args:
        stream (BinaryIO): input stream
        offset (int): Offset within the steam to read.
    
    Returns:
        int: 16-bit unsigned integer
    """
    return read_ndata(stream, 2, offset, '>H')

def read_u8(stream: BinaryIO, offset: int = None) -> int:
    """
    Read an 8-bit unsigned integer from a stream

    Args:
        stream (BinaryIO): input stream
        offset (int): Offset within the steam to read.
    
    Returns:
        int: 8-bit unsigned integer
    """
    return read_ndata(stream, 1, offset, '>B')


def read_s64(stream: BinaryIO, offset: int = None) -> int:
    """
    Read a 64-bit signed big-endian integer from a stream

    Args:
        stream (BinaryIO): input stream
        offset (int): Offset within the steam to read.
    
    Returns:
        int: 64-bit signed integer
    """
    return read_ndata(stream, 8, offset, '>q')

def read_s32(stream: BinaryIO, offset: int) -> int:
    """
    Read an 32-bit signed integer from a stream

    Args:
        stream (BinaryIO): input stream
        offset (int): Offset within the steam to read.
    
    Returns:
        int: 32-bit signed integer
    """
    return read_ndata(stream, 4, offset, '>i')

def read_s16(stream: BinaryIO, offset: int) -> int:
    """
    Read an 16-bit signed integer from a stream
    
    Args:
        stream (BinaryIO): input stream
        offset (int): Offset within the steam to read.
    
    Returns:
        int: 16-bit signed integer
    """
    return read_ndata(stream, 2, offset, '>h')

def read_s8(stream: BinaryIO, offset: int = None) -> int:
    """
    Read an 8-bit signed integer from a stream
    
    Args:
        stream (BinaryIO): input stream
        offset (int): Offset within the steam to read.
    
    Returns:
        int: 8-bit signed integer
    """
    return read_ndata(stream, 1, offset, '>b')

def read_float(stream: BinaryIO, offset: int = None) -> float:
    """
    Read a big-endian float from a stream
    
    Args:
        stream (BinaryIO): input stream
        offset (int): Offset within the steam to read.
    
    Returns:
        int: Big-endian float
    """
    return read_ndata(stream, 4, offset, '>f')

def read_string(stream: BinaryIO, number_of_bytes: int, offset: int = None, str_fmt: str = STRING_FORMAT, error_handling: str = "strict") -> str:
    """
    Read a string of set size from a stream. Will automatically split on a null byte.
    
    Args:
        stream (BinaryIO): input stream
        number_of_bytes: The number of bytes to read
        offset (int): Offset within the steam to read.
        str_fmt (str): Output decoding format.
        error_handling (str): See decode's "errors" field
    
    Returns:
        str: decoded string
    """    
    return read_ndata(stream, number_of_bytes, offset).split(b'\x00')[0].decode(str_fmt, errors=error_handling)

def read_string_until_null(stream: BinaryIO, offset: int, str_fmt: str = STRING_FORMAT, error_handling: str = "strict") -> str:
    """
    Read a string of until size is read or null byte is found from a stream
    
    Args:
        stream (BinaryIO): input stream
        offset (int): Offset within the steam to read.
        str_fmt (str): Output decoding format.
        error_handling (str): See decode's "errors" field
    
    Returns:
        str: decoded string
    """
    if not offset is None:
        stream.seek(offset)
    
    null_byte = '\0'.encode(str_fmt)
    chars = bytearray()
    while True:
        byte = stream.read(len(null_byte))
        if byte == null_byte or not byte:
            break
        chars += byte
    
    return chars.decode(str_fmt, errors=error_handling)

def read_bytes(stream: BinaryIO, size: int = -1, offset: int = None) -> bytes:
    """
    Reads a specific amount of requested bytes

    Args:
        stream (BinaryIO): input stream.
        size: The number of bytes to read. By default reads until the end of the file.
        offset (int): Offset within the steam to read.
    
    Returns:
        bytes: bytes object
    """
    return read_ndata(stream, size, offset)