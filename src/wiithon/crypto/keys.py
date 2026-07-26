from Crypto.Cipher import AES

from wiithon.crypto.layout import COMMON_KEYS
from wiithon.disc.enums import KeyType


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