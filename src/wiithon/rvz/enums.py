from enum import IntEnum

class WiaCompression(IntEnum):
    """Compression method of a WIA or RVZ file"""
    NONE  = 0
    PURGE = 1
    BZIP2 = 2
    LZMA  = 3
    LZMA2 = 4
    ZSTD  = 5

class WiaDiscType(IntEnum):
    """DiscType of a WIA or RVZ file"""
    UNKNOWN  = 0
    GAMECUBE = 1
    WII      = 2