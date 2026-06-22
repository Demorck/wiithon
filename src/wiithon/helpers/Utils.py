import struct
from typing import BinaryIO
from Crypto.Cipher import AES
import hashlib
import json
from typing import Any

STRING_FORMAT: str = "utf-8"

class ByteHelperError(Exception):
    pass

from wiithon.helpers.Constants import (
    COMMON_KEYS, SHA1_SIZE,

    BLOCK_HEADER_SIZE, BLOCK_PER_GROUP, BLOCK_SIZE,
    SUBGROUP_BY_GROUP, SUBBLOCK_SIZE, SUBBLOCK_BY_BLOCK,
    BLOCK_BY_SUBGROUP, SUBGROUP_SIZE
)

from wiithon.helpers.Enums import KeyType

###########################
####### READ UTILS ########
###########################
def read_u64(stream: BinaryIO, offset: int = None) -> int:
    """
    Read a 64-bit unsigned big-endian integer from a stream

    Args:
        stream (BinaryIO): input stream
        offset (int): Offset within the steam to read.
    
    Returns:
        int: 64-bit unsigned integer
    """
    length = 8
    if not offset is None:
        data_length = stream.seek(offset, 2)
        if offset + length > data_length:
            raise ByteHelperError(f"Offset {offset} + Length {length} is longer than the data size {data_length}.")
        stream.seek(offset)
    return struct.unpack('>Q', stream.read(length))[0]

def read_u32(stream: BinaryIO, offset: int = None) -> int:
    """
    Read a 32-bit unsigned big-endian integer from a stream

    Args:
        stream (BinaryIO): input stream
        offset (int): Offset within the steam to read.
    
    Returns:
        int:32-bit unsigned integer
    """
    length = 4
    if not offset is None:
        data_length = stream.seek(offset, 2)
        if offset + length > data_length:
            raise ByteHelperError(f"Offset {offset} + Length {length} is longer than the data size {data_length}.")
        stream.seek(offset)
    return struct.unpack('>I', stream.read(length))[0]

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
    length = 2
    if not offset is None:
        data_length = stream.seek(offset, 2)
        if offset + length > data_length:
            raise ByteHelperError(f"Offset {offset} + Length {length} is longer than the data size {data_length}.")
        stream.seek(offset)
    return struct.unpack('>H', stream.read(length))[0]

def read_u8(stream: BinaryIO, offset: int = None) -> int:
    """
    Read an 8-bit unsigned integer from a stream

    Args:
        stream (BinaryIO): input stream
        offset (int): Offset within the steam to read.
    
    Returns:
        int: 8-bit unsigned integer
    """
    length = 1
    if not offset is None:
        data_length = stream.seek(offset, 2)
        if offset + length > data_length:
            raise ByteHelperError(f"Offset {offset} + Length {length} is longer than the data size {data_length}.")
        stream.seek(offset)
    return struct.unpack('>B', stream.read(length))[0]

def read_s64(stream: BinaryIO, offset: int = None) -> int:
    """
    Read a 64-bit signed big-endian integer from a stream

    Args:
        stream (BinaryIO): input stream
        offset (int): Offset within the steam to read.
    
    Returns:
        int: 64-bit signed integer
    """
    length = 8
    if not offset is None:
        data_length = stream.seek(offset, 2)
        if offset + length > data_length:
            raise ByteHelperError(f"Offset {offset} + Length {length} is longer than the data size {data_length}.")
        stream.seek(offset)
    return struct.unpack('>q', stream.read(length))[0]

def read_s32(stream: BinaryIO, offset: int) -> int:
    """
    Read an 32-bit signed integer from a stream

    Args:
        stream (BinaryIO): input stream
        offset (int): Offset within the steam to read.
    
    Returns:
        int: 32-bit signed integer
    """
    length = 4
    if not offset is None:
        data_length = stream.seek(offset, 2)
        if offset + length > data_length:
            raise ByteHelperError(f"Offset {offset} + Length {length} is longer than the data size {data_length}.")
        stream.seek(offset)
    return struct.unpack(">i", stream.read(length))[0]

def read_s16(stream: BinaryIO, offset: int) -> int:
    """
    Read an 16-bit signed integer from a stream
    
    Args:
        stream (BinaryIO): input stream
        offset (int): Offset within the steam to read.
    
    Returns:
        int: 16-bit signed integer
    """
    length = 2
    if not offset is None:
        data_length = stream.seek(offset, 2)
        if offset + length > data_length:
            raise ByteHelperError(f"Offset {offset} + Length {length} is longer than the data size {data_length}.")
        stream.seek(offset)
    return struct.unpack(">h", stream.read(length))[0]

def read_s8(stream: BinaryIO, offset: int = None) -> int:
    """
    Read an 8-bit signed integer from a stream
    
    Args:
        stream (BinaryIO): input stream
        offset (int): Offset within the steam to read.
    
    Returns:
        int: 8-bit signed integer
    """
    length = 1
    if not offset is None:
        data_length = stream.seek(offset, 2)
        if offset + length > data_length:
            raise ByteHelperError(f"Offset {offset} + Length {length} is longer than the data size {data_length}.")
        stream.seek(offset)
    return struct.unpack(">b", stream.read(length))[0]

def read_float(stream: BinaryIO, offset: int = None) -> float:
    """
    Read a big-endian float from a stream
    
    Args:
        stream (BinaryIO): input stream
        offset (int): Offset within the steam to read.
    
    Returns:
        int: Big-endian float
    """
    length = 4
    if not offset is None:
        data_length = stream.seek(offset, 2)
        if offset + length > data_length:
            raise ByteHelperError(f"Offset {offset} + Length {length} is longer than the data size {data_length}.")
        stream.seek(offset)
    return struct.unpack(">f", stream.read(length))[0]

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
    if not offset is None:
        data_length = stream.seek(offset, 2)
        if offset + number_of_bytes > data_length:
            raise ByteHelperError(f"Offset {offset} + Length {number_of_bytes} is longer than the data size {data_length}.")
        stream.seek(offset)
    
    return stream.read(number_of_bytes).split(b'\x00')[0].decode(str_fmt, errors=error_handling)

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
    if not offset is None:
        data_length = stream.seek(offset, 2)
        if offset + size > data_length:
            raise ByteHelperError(f"Offset {offset} + Size {size} is longer than the data size {data_length}.")
        stream.seek(offset)
    return stream.read(size)

###########################
####### WRITE UTILS #######
###########################

def write_u64(stream: BinaryIO, new_value: int, offset: int = None):
    """
    Writes an 64-bit unsigned integer to a stream

    Args:
        stream (BinaryIO): input stream
        new_value (int): The value to write to stream
        offset (int): Offset within the steam to write.
    """
    new_bytes = struct.pack(">Q", new_value)
    if not offset is None:
        stream.seek(offset)
    stream.write(new_bytes)

def write_u32(stream: BinaryIO, new_value: int, offset: int = None):
    """
    Writes an 32-bit unsigned integer to a stream

    Args:
        stream (BinaryIO): input stream
        new_value (int): The value to write to stream
        offset (int): Offset within the steam to write.
    """
    new_bytes = struct.pack(">I", new_value)
    if not offset is None:
        stream.seek(offset)
    stream.write(new_bytes)

def write_u16(stream: BinaryIO, new_value: int, offset: int = None):
    """
    Writes an 16-bit unsigned integer to a stream

    Args:
        stream (BinaryIO): input stream
        new_value (int): The value to write to stream
        offset (int): Offset within the steam to write.
    """
    new_bytes = struct.pack(">H", new_value)
    if not offset is None:
        stream.seek(offset)
    stream.write(new_bytes)

def write_u8(stream: BinaryIO, new_value: int, offset: int = None):
    """
    Writes an 8-bit unsigned integer to a stream

    Args:
        stream (BinaryIO): input stream
        new_value (int): The value to write to stream
        offset (int): Offset within the steam to write.
    """
    new_bytes = struct.pack(">B", new_value)
    if not offset is None:
        stream.seek(offset)
    stream.write(new_bytes)

def write_s64(stream: BinaryIO, new_value: int, offset: int = None):
    """
    Writes an 64-bit signed integer to a stream

    Args:
        stream (BinaryIO): input stream
        new_value (int): The value to write to stream
        offset (int): Offset within the steam to write.
    """
    new_bytes = struct.pack(">q", new_value)
    if not offset is None:
        stream.seek(offset)
    stream.write(new_bytes)

def write_s32(stream: BinaryIO, new_value: int, offset: int = None):
    """
    Writes an 32-bit signed integer to a stream

    Args:
        stream (BinaryIO): input stream
        new_value (int): The value to write to stream
        offset (int): Offset within the steam to write.
    """
    new_bytes = struct.pack(">i", new_value)
    if not offset is None:
        stream.seek(offset)
    stream.write(new_bytes)

def write_s16(stream: BinaryIO, new_value: int, offset: int = None):
    """
    Writes an 16-bit signed integer to a stream

    Args:
        stream (BinaryIO): input stream
        new_value (int): The value to write to stream
        offset (int): Offset within the steam to write.
    """
    new_bytes = struct.pack(">h", new_value)
    if not offset is None:
        stream.seek(offset)
    stream.write(new_bytes)

def write_s8(stream: BinaryIO, new_value: int, offset: int = None):
    """
    Writes an 8-bit signed integer to a stream

    Args:
        stream (BinaryIO): input stream
        new_value (int): The value to write to stream
        offset (int): Offset within the steam to write.
    """
    new_bytes = struct.pack(">b", new_value)
    if not offset is None:
        stream.seek(offset)
    stream.write(new_bytes)

def write_float(stream: BinaryIO, new_value: float, offset: int = None):
    """
    Writes a float to a stream

    Args:
        stream (BinaryIO): input stream
        new_value (float): The value to write to stream
        offset (int): Offset within the steam to write.
    """
    new_bytes = struct.pack(">f", new_value)
    if not offset is None:
        stream.seek(offset)
    stream.write(new_bytes)

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
        raise ByteHelperError(f"String \"{new_value}\" is too long (max length: {str(expected_size)})")

    padding_length = expected_size - str_len
    new_value = encoded_string + (padding_byte * padding_length)

    if add_null_byte:
        new_value += b'\0'

    if not offset is None:
        stream.seek(offset)

    stream.write(new_value)
    

def write_bytes(stream: BinaryIO, new_bytes: bytes, offset: int = None):
    """
    Writes raw bytes into the given stream
    
    Args:
        stream (BinaryIO): input stream
        new_value (bytes): The value to write to stream
        offset (int): Offset within the steam to write.
    """

    if not offset is None:
        stream.seek(offset)
    stream.write(new_bytes)

###########################
### CRYPTOGRAPHIC UTILS ###
###########################

def decrypt_title_key(encrypted_key: bytes, common_key_index: int, title_id: bytes) -> bytes:
    """
    Decrypt the title key using the common key and title ID as IV

    - Build the IV: title_id (8 bytes) + 8 zero bytes
    - Select the right common key by index
    - Decrypt with AES-128-CBC

    The resulting title key will be used to decrypt all data block in the partition
    :param encrypted_key: Encrypted title key
    :param common_key_index: Common key index
    :param title_id: Title ID
    :return: Decrypted title key
    """
    iv: bytes = title_id + b'\x00' * 8 # 16 bytes and the first 8 are the title id
    cipher = AES.new(COMMON_KEYS[common_key_index], AES.MODE_CBC, iv)
    return cipher.decrypt(encrypted_key)

def encrypt_title_key(decrypted_key: bytes, common_key_index: int, title_id: bytes) -> bytes:
    """
    Encrypt the title key using the common key and title ID as IV

    :param decrypted_key: Decrypted title key
    :param common_key_index: Common key index
    :param title_id: Title ID
    :return: Decrypted title key
    """
    iv: bytes = title_id + b'\x00' * 8 # 16 bytes and the first 8 are the title id
    cipher = AES.new(COMMON_KEYS[common_key_index], AES.MODE_CBC, iv)
    return cipher.encrypt(decrypted_key)

def get_length_from_key_type(key_type: KeyType) -> (int, int, int):
    """
    Return (key_size, exponent_size, padding_size) for a certificate key type

    Used when reading/writing to know how many bytes to read/write and its padding

    :param key_type: Key type from the certificate
    :return: Tuple (key_size, exponent_size, padding_size)
    """
    match key_type:
        case KeyType.NONE:
            raise ValueError("Invalid key type")
        case KeyType.RSA_4096:
            return 0x200, 0x04, 0x34
        case KeyType.RSA_2048:
            return 0x100, 0x04, 0x34
        case KeyType.ECC_B233:
            return 0x3C, 0x00, 0x3C

    raise ValueError("Invalid key type")


def decrypt_block(block: bytes, title_key: bytes) -> bytes:
    """
    Decrypt a single 0x8000-byte block

    - Extracts the IV at offset: 0x3D0 of the block header (16 bytes)
    - Decrypts the data section (0x400 to end) with AES-128-CBC
    - Returns the 0x7C00 bytes, decrypted

    See: https://wiibrew.org/wiki/Wii_disc#Encrypted
    :param block: Raw encrypted block
    :param title_key: 16-byte title key
    :return: decrypted data (0x7C00)
    """
    data_iv = block[0x3D0:0x3E0]
    data_cipher = AES.new(title_key, AES.MODE_CBC, data_iv)
    data_section = data_cipher.decrypt(block[BLOCK_HEADER_SIZE:])

    return data_section

def decrypt_group(group_data: bytes, title_key: bytes) -> bytes:
    """
    Decrypt an entire group of 64 blocks.
    Iterates over all 64 blocks in the group, decrypt each one and concatenates

    :param group_data: Raw encrypted group
    :param title_key: 16-byte title key
    :return: Decrypted group
    """
    result = bytearray()
    for i in range(BLOCK_PER_GROUP):
        current_block_start = i * BLOCK_SIZE
        current_block = group_data[current_block_start: current_block_start + BLOCK_SIZE]
        result.extend(decrypt_block(current_block, title_key))

    return result


def encrypt_group(group_data: bytes | bytearray, title_key: bytes, h3_ref: bytearray | None = None) -> bytes:
    """
    Hash and encrypt a full 2MB group
    Reference: https://wiibrew.org/wiki/Wii_disc#Encrypted

    :param group_data: 2MB bytes/bytearray to be hashed and encrypted
    :param title_key: 16-byte decrypted title key
    :param h3_ref: Optional bytearray of length 20 where the H3 hash will be stored
    :return: The encrypted 2MB data as bytes
    """
    buffer = bytearray(group_data)

    hasher = hashlib.sha1
    h2 = bytearray(SHA1_SIZE * SUBGROUP_BY_GROUP)

    # H2 loop
    for subgroup_index in range(SUBGROUP_BY_GROUP):
        h1 = bytearray(SHA1_SIZE * BLOCK_BY_SUBGROUP)

        # H1 loop
        for block_index in range(BLOCK_BY_SUBGROUP):
            block_start = subgroup_index * SUBGROUP_SIZE + block_index * BLOCK_SIZE
            h0 = bytearray(SHA1_SIZE * SUBBLOCK_BY_BLOCK)

            # H0 loop: all "subblock" hashes
            for j in range(SUBBLOCK_BY_BLOCK):
                data_subblock = buffer[
                                    block_start + (j + 1) * SUBBLOCK_SIZE:
                                    block_start + (j + 2) * SUBBLOCK_SIZE
                                ]

                # Putting the hash of the subblock in the right place in the h0 table
                h0[j * SHA1_SIZE:(j + 1) * SHA1_SIZE] = hasher(data_subblock).digest()

            # Hashing h0 and placing it in the right place in the h1 table
            h1[block_index * SHA1_SIZE:(block_index + 1) * SHA1_SIZE] = hasher(h0).digest()

            # Placing H0 in the block header then the padding
            buffer[block_start: block_start + len(h0)] = h0
            buffer[block_start + len(h0): block_start + 0x280] = b'\x00' * 0x14

        # Hashing h1 and placing it in the right place
        h2[subgroup_index * SHA1_SIZE:(subgroup_index + 1) * SHA1_SIZE] = hasher(h1).digest()

        # Placing H1 in the block header
        for block_index in range(BLOCK_BY_SUBGROUP):
            block_start = subgroup_index * SUBGROUP_SIZE + block_index * BLOCK_SIZE
            buffer[block_start + 0x280: block_start + 0x280 + len(h1)] = h1
            buffer[block_start + 0x320: block_start + 0x340] = b'\x00' * 0x20

    # Calculate H3
    if h3_ref is not None:
        h3_ref[:] = hasher(h2).digest()

    # Placing H2 and encrypt
    for subgroup_index in range(SUBGROUP_BY_GROUP):
        for block_index in range(BLOCK_BY_SUBGROUP):
            block_start = subgroup_index * SUBGROUP_SIZE + block_index * BLOCK_SIZE

            # Placing H2 in the block header
            buffer[block_start + 0x340: block_start + 0x340 + len(h2)] = h2
            buffer[block_start + 0x3E0: block_start + 0x400] = b'\x00' * 0x20

            cipher = AES.new(title_key, AES.MODE_CBC, b'\x00' * 16)
            buffer[block_start: block_start + 0x400] = cipher.encrypt(bytes(buffer[block_start: block_start + 0x400]))

            # Encrypt data with the last 16 bytes (before padding) of encrypted header
            iv = buffer[block_start + 0x3D0: block_start + 0x3E0]
            cipher2 = AES.new(title_key, AES.MODE_CBC, bytes(iv))
            buffer[block_start + 0x400: block_start + BLOCK_SIZE] = cipher2.encrypt(
                bytes(buffer[block_start + 0x400: block_start + BLOCK_SIZE])
            )

    return bytes(buffer)


###########################
########## UTILS ##########
###########################
def align(value: int, boundary: int) -> int:
    return (value + boundary - 1) & ~(boundary - 1)

###########################
####### PRINT UTILS #######
###########################
def _parse_value(key: str, val: Any) -> Any:
    """Analyse et convertit récursivement en gardant une trace de la clé."""

    if hasattr(val, "__dict__"):
        return {
            k: _parse_value(k, v)  # On passe le nom de l'attribut (k) pour la suite
            for k, v in val.__dict__.items()
            if not k.startswith('_')
        }
    elif isinstance(val, list):
        # Pour une liste, on conserve la clé parente (ex: si c'est la liste 'game_id')
        return [_parse_value(key, i) for i in val]
    elif isinstance(val, bytes):

        # --- L'EXCEPTION EST ICI ---
        # Si la clé est 'game_id' (ou d'autres champs texte), on tente de décoder
        if key in ["game_id", "title_id"]:
            # On utilise errors='ignore' au cas où, et strip('\x00') pour
            # enlever les octets nuls de fin de chaîne (très commun dans les headers Wii)
            return val.decode("utf-8", errors="ignore").strip('\x00')

        # Comportement par défaut pour le reste des bytes
        return f"0x{val.hex().upper()}"

    elif hasattr(val, "read") and hasattr(val, "seek"):
        return "<Fichier binaire ouvert>"
    elif isinstance(val, int) and val > 0xFFFF:
        return hex(val)

    return val


def build_json_repr(obj: Any) -> str:
    class_name = obj.__class__.__name__
    # On initialise avec une clé bidon (ex: le nom de la classe)
    data = _parse_value(class_name, obj)
    json_content = json.dumps(data, indent=4, ensure_ascii=False)
    return f"{class_name} {json_content}"

def json_repr(cls):
    """Décorateur pour injecter un __repr__ au format JSON."""
    cls.__repr__ = lambda self: build_json_repr(self)
    return cls
