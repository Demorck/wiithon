"""
Cryptographic constants and block-structure parameters for Wii encryption

- Common keys (AES-128) used to decrypt the title key from the Ticket
- Block & Group size parameters
"""

# Raw block size on disc (header + encrypted data) - 32KB
BLOCK_SIZE       : int = 0x8000
# Header size per block (contains H0/H1/H2 hashes and AES IV)
BLOCK_HEADER_SIZE: int = 0x400
# Number of blocks in a group
BLOCK_PER_GROUP  : int = 64
# Usable data per block (So, without the header): 0x8000 - 0x400 = 0x7C00 (31 744 bytes)
BLOCK_DATA_SIZE  : int = BLOCK_SIZE - BLOCK_HEADER_SIZE
# Raw group size (0x8000 * 64 = 0x200000 - 2MB)
GROUP_SIZE       : int = BLOCK_SIZE * BLOCK_PER_GROUP
# Usable data per group (0x7C00 * 64 = 0x1F0000 - 1,9375MB)
GROUP_DATA_SIZE  : int = BLOCK_DATA_SIZE * BLOCK_PER_GROUP

# Each user data of each block has 0x400. So, 0x7C00 / 0x400 = 0d31
SUBBLOCK_BY_BLOCK: int = 31
BLOCK_BY_SUBGROUP: int = 8
SUBGROUP_BY_GROUP: int = 8

SUBBLOCK_SIZE : int = BLOCK_DATA_SIZE // SUBBLOCK_BY_BLOCK

SHA1_SIZE: int = 20

# Subgroup size for encryption (0x8000 * 8 = 0x40 000)
SUBGROUP_SIZE: int = BLOCK_SIZE * BLOCK_BY_SUBGROUP