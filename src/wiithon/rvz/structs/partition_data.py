from typing import BinaryIO

from wiithon.binary.reader import BinaryReader
from wiithon.crypto.layout import BLOCK_SIZE


class WiaPartitionData:
    """
    One of the two segments of a partition.
    """

    def __init__(self) -> None:
        """
        Constructor
        """
        #: Where the first block this segment start
        self.first_block: int = 0

        #: How many disc blocks it covers
        self.block_count: int = 0

        #: Index of the first group holding this segment. The other follow it directly
        self.group_index: int = 0

        #: The number of group struct
        self.group_count: int = 0

    @property
    def offset(self) -> int:
        """
        Absolute disc offset this segment starts at

        Returns:
            The offset hashes included in the count
        """
        return self.first_block * BLOCK_SIZE

    @classmethod
    def read(cls, stream: BinaryIO) -> "WiaPartitionData":
        """
        Read the partition data from a stream

        Args:
            stream: The current stream of the file

        Returns:
            The object created
        """
        obj = cls()
        reader = BinaryReader(stream)

        obj.first_block = reader.u32()
        obj.block_count = reader.u32()
        obj.group_index = reader.u32()
        obj.group_count = reader.u32()

        return obj