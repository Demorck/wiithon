from typing import BinaryIO

from wiithon.binary.reader import BinaryReader
from wiithon.crypto.layout import BLOCK_HEADER_SIZE, SHA1_SIZE


class WiaException:
    """
    One difference between a hash the reader recomputes and the one from the original iso
    """

    def __init__(self) -> None:
        """
        Constructor
        """
        #: Where the hash is among the block headers of the chunk
        self.offset: int = 0

        #: Value recomputed hash that must be replaced
        self.hash: bytes = b'\x00' * SHA1_SIZE

    @property
    def block(self) -> int:
        """
        Which block of the chunk this exception is
        The doc says: "The offsets 0x0000-0x0400 here map to the offsets 0x0000-0x0400 in the full 2 MiB of data,
        the offsets 0x0400-0x0800 here map to the offsets 0x8000-0x8400 in the full 2 MiB of data, and so on."

        Returns:
            The block index
        """
        return self.offset // BLOCK_HEADER_SIZE

    @property
    def offset_in_block(self) -> int:
        """
        Which offset in a block the hash is
        The doc says: "The offsets 0x0000-0x0400 here map to the offsets 0x0000-0x0400 in the full 2 MiB of data,
        the offsets 0x0400-0x0800 here map to the offsets 0x8000-0x8400 in the full 2 MiB of data, and so on."

        Returns:
            An offset from 0x000 to 0x400
        """
        return self.offset % BLOCK_HEADER_SIZE

    @classmethod
    def read(cls, stream: BinaryIO) -> 'WiaException':
        """
        Read one exception

        Args:
            stream: Current stream of the file

        Returns:
            The object created
        """
        obj = cls()
        reader = BinaryReader(stream)

        obj.offset = reader.u16()
        obj.hash   = reader.raw(SHA1_SIZE)

        return obj