"""
Cryptographic constants abd block-structure parameters for Wii encryption

- Common keys (AES-128) used to decrypt the title key from the Ticket
- Block & Group size parameters
"""

# "Normal" Common key. Used by the majority of Wii games
# 16 bytes AES-128 key, index 0 in the Ticket
COMMON_KEY_NORMAL = bytes([
    0xeb, 0xe4, 0x2a, 0x22, 0x5e, 0x85, 0x93, 0xe4,
    0x48, 0xd9, 0xc5, 0x45, 0x73, 0x81, 0xaa, 0xf7
])

# Korean Common key. Used for korean titles ofc
# index 1 in the Ticket
COMMON_KEY_KOREAN = bytes([
    0x63, 0xb8, 0x2b, 0xb4, 0xf4, 0x61, 0x4e, 0x2e,
    0x13, 0xf2, 0xfe, 0xfb, 0xba, 0x4c, 0x9b, 0x7e
])

# Indexed by the common_key_index field from the Ticket:
#   - 0 -> COMMON_KEY_NORMAL
#   - 1 -> COMMON_KEY_KOREAN
COMMON_KEYS = [COMMON_KEY_NORMAL, COMMON_KEY_KOREAN]

# Raw block size on disc (header + encrypted data) - 32KB
BLOCK_SIZE       : int = 0x8000
# Header size per block (contains H0/H1/H2 hashes and AES IV)
BLOCK_HEADER_SIZE: int = 0x400
# Number of blocks in a group
BLOCk_PER_GROUP  : int = 64
# Usable data per block (So, without the header): 0x8000 - 0x400 = 0x7C00 (31 744 bytes)
BLOCK_DATA_SIZE  : int = BLOCK_SIZE - BLOCK_HEADER_SIZE
# Raw group size (0x8000 * 64 = 0x200000 - 2MB)
GROUP_SIZE       : int = BLOCK_SIZE * BLOCk_PER_GROUP
# Usable data per group (0x7C00 * 64 = 0x1F0000 - 1,9375MB)
GROUP_DATA_SIZE  : int = BLOCK_DATA_SIZE * BLOCk_PER_GROUP

# Each user data of each block has 0x400. So, 0x7C00 / 0x400 = 0d31
SUBBLOCK_BY_BLOCK: int = 31
BLOCK_BY_SUBGROUP: int = 8
SUBGROUP_BY_GROUP: int = 8

SUBBLOCK_SIZE : int = BLOCK_DATA_SIZE // SUBBLOCK_BY_BLOCK

SHA1_SIZE: int = 20

# Subgroup size for encryption (0x8000 * 8 = 0x40 000)
SUBGROUP_SIZE: int = BLOCK_SIZE * BLOCK_BY_SUBGROUP