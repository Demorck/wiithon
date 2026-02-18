import struct
from typing import BinaryIO
from Crypto.Cipher import AES

from Constants import COMMON_KEYS
from Enums import SignatureType, KeyType


###########################
####### BYTES UTILS #######
###########################

# Wanted to create a function for n bytes at 0x00 but useless ?

###########################
#### READ/WRITE UTILS #####
###########################
def read_u64(stream: BinaryIO) -> int:
    """
    Read a 64-bit unsigned integer from a stream
    :param stream: Binary IO stream
    :return: 64-bit unsigned integer
    """
    return struct.unpack('>Q', stream.read(8))[0]


def read_u32(stream: BinaryIO) -> int:
    """
    Read a 32-bit unsigned integer from a stream
    :param stream: Binary IO stream
    :return: 32-bit unsigned integer
    """
    return struct.unpack('>I', stream.read(4))[0]

def read_u16(stream: BinaryIO) -> int:
    """
    Read a 16-bit unsigned integer from a stream
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
    Read a 64-bit unsigned integer from a stream (an u32 shifted two times to the right)
    :param stream: Binary IO stream
    :return: 64-bit unsigned integer
    """
    return read_u32(stream) << 2




###########################
### CRYPTOGRAPHIC UTILS ###
###########################

def decrypt_title_key(encrypted_key: bytes, common_key_index: int, title_id: bytes) -> bytes:
    """
    Decrypt the title key using the common key and title ID as IV
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