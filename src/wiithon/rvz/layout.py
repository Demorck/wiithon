from typing import NamedTuple, Optional

#: WIA Magic Word
WIA_MAGIC_WORD: bytes = b'WIA\x01'
#: RVZ Magic word
RVZ_MAGIC_WORD: bytes = b'RVZ\x01'

#: Where the header starts
HEADER_OFFSET: int = 0x00
#: Size of the header
HEADER_SIZE  : int = 0x48
#: Offset of the hash of the header
HEADER_HASH  : int = 0x34

#: Offset of the disc struct, just after the header above
DISC_OFFSET:            int = HEADER_OFFSET + HEADER_SIZE
#: Size of the disc struct
DISC_SIZE:              int = 0xDC
#: First 0x80 bytes of the disc image
DHEAD_SIZE:             int = 0x80
#: Compressor specific data
COMPRESSOR_DATA_SIZE:   int = 0x07

PARTITION_DATA_SIZE:        int = 0x10
PARTITION_TITLE_KEY_SIZE:   int = 0x10
PARITITION_SEGMENT:         int = 0x02
PARTITION_SIZE:             int = PARITITION_SEGMENT * PARTITION_DATA_SIZE + PARTITION_TITLE_KEY_SIZE
RAW_DATA_SIZE:              int = 0x18
WIA_GROUP_SIZE:             int = 0x08
RVZ_GROUP_SIZE:             int = 0x0C


MIN_CHUNK_SIZE: int = 0x8000
WIA_CHUNK_UNIT: int = 0x200000