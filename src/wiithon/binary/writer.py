import struct
from typing import BinaryIO, Any

from wiithon.binary.common import STRING_FORMAT
from wiithon.exceptions import BinaryError


###########################
####### WRITE UTILS #######
###########################

def write_ndata(stream: BinaryIO, new_value: Any, offset: int = None, pack_fmt: str = None):
    """
    Write n size data and converts it to the expected data type/size.

    Args:
        stream (BinaryIO): input stream
        new_value (Any): new value to be written in pack_format (assumes data is already bytes by default)
        offset (int): Offset within the steam to read.
        pack_fmt (str): If specified, unpacks the bytes into a specific output type.
    """
    if offset is not None:
        stream.seek(offset)

    new_bytes = new_value
    if pack_fmt is not None:
        new_bytes = struct.pack(pack_fmt, new_value)
    return stream.write(new_bytes)


def write_u64(stream: BinaryIO, new_value: int, offset: int = None):
    """
    Writes an 64-bit unsigned integer to a stream

    Args:
        stream (BinaryIO): input stream
        new_value (int): The value to write to stream
        offset (int): Offset within the steam to write.
    """
    write_ndata(stream, new_value, offset, ">Q")


def write_u32(stream: BinaryIO, new_value: int, offset: int = None):
    """
    Writes an 32-bit unsigned integer to a stream

    Args:
        stream (BinaryIO): input stream
        new_value (int): The value to write to stream
        offset (int): Offset within the steam to write.
    """
    write_ndata(stream, new_value, offset, ">I")


def write_u16(stream: BinaryIO, new_value: int, offset: int = None):
    """
    Writes an 16-bit unsigned integer to a stream

    Args:
        stream (BinaryIO): input stream
        new_value (int): The value to write to stream
        offset (int): Offset within the steam to write.
    """
    write_ndata(stream, new_value, offset, ">H")


def write_u8(stream: BinaryIO, new_value: int, offset: int = None):
    """
    Writes an 8-bit unsigned integer to a stream

    Args:
        stream (BinaryIO): input stream
        new_value (int): The value to write to stream
        offset (int): Offset within the steam to write.
    """
    write_ndata(stream, new_value, offset, ">B")


def write_s64(stream: BinaryIO, new_value: int, offset: int = None):
    """
    Writes an 64-bit signed integer to a stream

    Args:
        stream (BinaryIO): input stream
        new_value (int): The value to write to stream
        offset (int): Offset within the steam to write.
    """
    write_ndata(stream, new_value, offset, ">q")


def write_s32(stream: BinaryIO, new_value: int, offset: int = None):
    """
    Writes an 32-bit signed integer to a stream

    Args:
        stream (BinaryIO): input stream
        new_value (int): The value to write to stream
        offset (int): Offset within the steam to write.
    """
    write_ndata(stream, new_value, offset, ">i")


def write_s16(stream: BinaryIO, new_value: int, offset: int = None):
    """
    Writes an 16-bit signed integer to a stream

    Args:
        stream (BinaryIO): input stream
        new_value (int): The value to write to stream
        offset (int): Offset within the steam to write.
    """
    write_ndata(stream, new_value, offset, ">h")


def write_s8(stream: BinaryIO, new_value: int, offset: int = None):
    """
    Writes an 8-bit signed integer to a stream

    Args:
        stream (BinaryIO): input stream
        new_value (int): The value to write to stream
        offset (int): Offset within the steam to write.
    """
    write_ndata(stream, new_value, offset, ">b")


def write_float(stream: BinaryIO, new_value: float, offset: int = None):
    """
    Writes a float to a stream

    Args:
        stream (BinaryIO): input stream
        new_value (float): The value to write to stream
        offset (int): Offset within the steam to write.
    """
    write_ndata(stream, new_value, offset, ">f")


def write_string(stream: BinaryIO, new_value: str, expected_size: int, padding_byte: bytes = b'\0',
                 offset: int = None, str_fmt: str = STRING_FORMAT, add_null_byte: bool = False):
    """
    Writes a str to a stream

    Args:
        stream (BinaryIO): input stream
        new_value (str): The value to write to stream
        expected_size (int): Checks the size of encoded string is the expected byte length, otherwise adds X padding_byte
        padding_byte (bytes): byte to padd the string to match X expected size.
        offset (int): Offset within the steam to write.
        str_fmt (str): Encoding format.
        add_null_byte (bool): Terminates the string with an extra null byte.
    """

    encoded_string = new_value.encode(str_fmt)
    str_len = len(encoded_string)
    if str_len > expected_size:
        raise BinaryError(f"String \"{new_value}\" is too long (max length: {str(expected_size)})")

    padding_length = expected_size - str_len
    new_value = encoded_string + (padding_byte * padding_length)

    if add_null_byte:
        new_value += b'\0'

    write_ndata(stream, new_value, offset)


def write_bytes(stream: BinaryIO, new_bytes: bytes, offset: int = None):
    """
    Writes raw bytes into the given stream

    Args:
        stream (BinaryIO): input stream
        new_value (bytes): The value to write to stream
        offset (int): Offset within the steam to write.
    """
    write_ndata(stream, new_bytes, offset)