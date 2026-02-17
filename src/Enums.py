from enum import IntEnum

class WiiPartType(IntEnum):
    """Wii Partition type"""
    DATA = 0x01
    UPDATE = 0x02
    CHANNEL = 0x03


class SignatureType(IntEnum):
    """
    Signature type.
    Used in tickets, TMD and certificates
    """
    NONE     = 0x00000000
    RSA_4096 = 0x00010000
    RSA_2048 = 0x00010001
    ELLIPSIS = 0x00010002

class KeyType(IntEnum):
    """
    Key type in certificate
    """
    RSA_4096 = 0x00000000
    RSA_2048 = 0x00000001