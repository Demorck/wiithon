import struct

FLAG = b"NEXT"
DATA_KEY = bytes.fromhex("0e5b5db26d4b71fd91a6eb12afed1796")
FIRST_SEGMENT = struct.pack(">IIII", 7940, 256, 127, 4)
SECOND_SEGMENT = struct.pack(">IIII", 8196, 134772, 131, 2106)
PARTITION = DATA_KEY + FIRST_SEGMENT + SECOND_SEGMENT

def exception_bytes(offset: int, digest: bytes = bytes(20)) -> bytes:
    """One exception entry: where the hash goes, then the hash itself"""
    return struct.pack(">H", offset) + digest
