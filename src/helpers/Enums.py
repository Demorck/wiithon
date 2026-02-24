from enum import IntEnum
"""
Some enumerations for partitions types, signatures, keys
"""

class WiiPartType(IntEnum):
    """
    Wii Partition type, read from the partition table at 0x40000
    Each disc partition is associated with one of these types
    Smash bros brawl seems to have 14 (??) partitions. The builtin virtual console has a partition for each game
    """
    DATA = 0x01 # Main partition, containing the game
    UPDATE = 0x02 # For Wii System update
    CHANNEL = 0x03 # Used for channel like Wii Fit, Mario Kart Wii


class SignatureType(IntEnum):
    """
    Cryptographic signature type (Signed Blob Header)
    Used in Tickets, TMDs and Certificates to identify the signature algorithm
    """
    NONE     = 0xFFFFFFFF # Not present, just for python
    RSA_4096 = 0x00010000 # RSA-4096:   0x200 byte signature
    RSA_2048 = 0x00010001 # RSA-2048:   0x100 byte signature
    ELLIPSIS = 0x00010002 # ECC:        0x40 byte signature

class KeyType(IntEnum):
    """
    Public Key type in certificate
    """
    NONE     = 0xFFFFFFFF # Not present, just for python
    RSA_4096 = 0x00000000 # RSA-4096:   0x200 byte key
    RSA_2048 = 0x00000001 # RSA-2048:   0x100 byte key
    ECC_B233 = 0x00000002 # ECC on B233 curve:   0x3C  byte key