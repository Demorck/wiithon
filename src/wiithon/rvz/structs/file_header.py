import hashlib
from typing import BinaryIO

from wiithon.binary.reader import BinaryReader
from wiithon.crypto.layout import SHA1_SIZE
from wiithon.exceptions import CorruptedDataError, InvalidFormatError
from wiithon.rvz.layout import HEADER_HASH, HEADER_SIZE, RVZ_MAGIC_WORD, WIA_MAGIC_WORD


class WiaHeader:
    """
    The first 0x48 bytes at offset 0.
    """

    def __init__(self) -> None:
        """
        Constructor.
        """
        #: Magic word of the header. WIA\x1 = WIA, RVZ\1 = RVZ
        self.magic: bytes = b''

        #: Version of the WIA format
        self.version: int = 0

        #: For reader program, to know if they support this version
        self.version_compatible: int = 0

        #: The size of the disc structure.
        self.disc_size: int = 0

        #: SHA1 hash of the disc struct. The number of bytes is determined by ``disc_size``
        self.disc_hash: bytes = b'' * SHA1_SIZE

        #: Size of the original disc
        self.iso_file_size: int = 0

        #: Size of the current file
        self.wia_file_size: int = 0

        #: SHA1 hash of the head (but not itself otherwise we have a problem to create it)
        self.head_hash: bytes = b'' * SHA1_SIZE

    @property
    def is_rvz(self) -> bool:
        return self.magic == RVZ_MAGIC_WORD

    @classmethod
    def read(cls, stream: BinaryIO) -> 'WiaHeader':
        """
        Read and validate the file header

        Args:
            stream: The current stream of the file

        Returns:
            The object created

        Raises:
            InvalidFormatError: If the magic is not WIA or RVZ
            CorruptedDataError: If the header hash is invalid so the header may be corrupted
        """
        obj = cls()
        raw = BinaryReader(stream).raw(HEADER_SIZE)
        reader = BinaryReader.from_bytes(raw)

        obj.magic = reader.raw(4)
        if obj.magic not in (WIA_MAGIC_WORD, RVZ_MAGIC_WORD):
            raise InvalidFormatError(f"Not a WIA or RVZ file, got magic {obj.magic!r}")

        obj.version            = reader.u32()
        obj.version_compatible = reader.u32()
        obj.disc_size          = reader.u32()
        obj.disc_hash          = reader.raw(SHA1_SIZE)
        obj.iso_file_size      = reader.u64()
        obj.wia_file_size      = reader.u64()
        obj.head_hash          = reader.raw(SHA1_SIZE)

        current_hash = hashlib.sha1(raw[:HEADER_HASH]).digest()
        if current_hash != obj.head_hash:
            raise CorruptedDataError("File header in WIA/RVZ has a hash mismatch")

        return obj