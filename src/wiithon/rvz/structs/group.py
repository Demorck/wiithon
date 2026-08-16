from typing import BinaryIO

from wiithon.binary.reader import BinaryReader
from wiithon.rvz.layout import GROUP_COMPRESSED_FLAG, GROUP_SIZE_MASK, RVZ_GROUP_SIZE, WIA_GROUP_SIZE


class WiaGroup:
    """
    A pointer to one chunk of disc data, compressed
    """

    #: Size of this structure
    STRUCT_SIZE: int = WIA_GROUP_SIZE

    def __init__(self) -> None:
        """
        Constructor
        """
        #: Offset in the file where the compressed data is
        self.offset: int = 0

        #: Size of compressed data, including exceptions lists
        self.size: int = 0

        #: RVZ only - True if it's compressed by the compression defined in the disc struct
        self.compressed: bool = True

        #: The size after decompressing but before decoding the RVZ packing
        #: Zero means RVZ is not used (so WIA)
        self.packed_size: int = 0

    @property
    def is_zero(self) -> bool:
        """
        If the chunk is 0x00 and carries no hash exception

        Returns:
            True if nothing is stored
        """
        return self.size == 0

    @property
    def is_packed(self) -> bool:
        """
        If the RVZ packing need to be decoded after decompression

        Returns:
            True if the chunk is packed
        """
        return self.packed_size != 0

    @classmethod
    def read(cls, stream: BinaryIO) -> "WiaGroup":
        """
        Read a WiaGroup from a stream

        Args:
            stream: THe current stream of the file

        Returns:
            WiaGroup created object
        """
        obj = cls()
        reader = BinaryReader(stream)

        obj.offset  = reader.u32_shifted()
        obj.size    = reader.u32()

        return obj


class RvzGroup(WiaGroup):
    """
    Same as WiaGroup, extended by RVZ with a packed size and a compression flag
    """

    #: Size of this structure
    STRUCT_SIZE: int = RVZ_GROUP_SIZE

    @classmethod
    def read(cls, stream: BinaryIO) -> "WiaGroup":
        """
        Read a RvzGroup from a stream

        Args:
            stream: THe current stream of the file

        Returns:
            RvzGroup created object
        """
        obj = cls()
        reader = BinaryReader(stream)

        obj.offset      = reader.u32_shifted()
        size            = reader.u32()
        obj.compressed  = bool(size & GROUP_COMPRESSED_FLAG)
        obj.size        = size & GROUP_SIZE_MASK
        obj.packed_size = reader.u32()

        return obj