import struct
from typing import BinaryIO
from Crypto.Cipher import AES

from helpers.Constants import *
from helpers.Enums import SignatureType, KeyType


###########################
####### BYTES UTILS #######
###########################

# Wanted to create a function for n bytes at 0x00 but useless ?

###########################
#### READ/WRITE UTILS #####
###########################
def read_u64(stream: BinaryIO) -> int:
    """
    Read a 64-bit unsigned big-endian integer from a stream
    :param stream: Binary IO stream
    :return: 64-bit unsigned integer
    """
    return struct.unpack('>Q', stream.read(8))[0]


def read_u32(stream: BinaryIO) -> int:
    """
    Read a 32-bit unsigned big-endian integer from a stream
    :param stream: Binary IO stream
    :return: 32-bit unsigned integer
    """
    return struct.unpack('>I', stream.read(4))[0]

def read_u16(stream: BinaryIO) -> int:
    """
    Read a 16-bit unsigned big-endian integer from a stream
    :param stream: Binary IO stream
    :return: 16-bit unsigned integer
    """
    return struct.unpack('>H', stream.read(2))[0]

def read_u8(stream: BinaryIO) -> int:
    """
    Read an 8-bit unsigned integer from a stream
    :param stream: Binary IO stream
    :return: 8-bit unsigned integer
    """
    return struct.unpack('>B', stream.read(1))[0]

def read_u64_shifted(stream: BinaryIO) -> int:
    """
    Read an u32 and left-shift it by 2 bits (x4)
    :param stream: Binary IO stream
    :return: 64-bit unsigned integer
    """
    return read_u32(stream) << 2

def read_string(stream: BinaryIO, number_of_bytes: int) -> str:
    """
    Read a string from a stream
    :param stream: The Binary IO stream
    :param number_of_bytes: The number of bytes to read
    :return: The returned string
    """
    return stream.read(number_of_bytes).split(b'\x00')[0].decode('ascii')

def read_shiftjis(stream: BinaryIO, offset: int) -> str:
    """
    Read a shift JS from a stream at a current offset

    TODO: doesn't work without the try-except, maybe need to know why ?
    :param stream: The Binary IO stream
    :param offset: The current offset
    :return: shift JS string
    """
    stream.seek(offset)
    chars = bytearray()
    while True:
        byte = stream.read(1)
        if byte == b'\x00' or not byte:
            break

        chars += byte

    try:
        return chars.decode('shift_jis')
    except UnicodeDecodeError:
        return chars.decode('shift_jis', errors='replace')

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

def encrypt_title_key(encrypted_key: bytes, common_key_index: int, title_id: bytes) -> bytes:
    """
    Encrypt the title key using the common key and title ID as IV

    :param encrypted_key: Encrypted title key
    :param common_key_index: Common key index
    :param title_id: Title ID
    :return: Encrypted title key
    """
    iv: bytes = title_id + b'\x00' * 8 # 16 bytes and the first 8 are the title id
    cipher = AES.new(COMMON_KEYS[common_key_index], AES.MODE_CBC, iv)
    return cipher.encrypt(encrypted_key)

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
    for i in range(BLOCk_PER_GROUP):
        current_block_start = i * BLOCK_SIZE
        current_block = group_data[current_block_start: current_block_start + BLOCK_SIZE]
        result.extend(decrypt_block(current_block, title_key))

    return result