from typing import BinaryIO

from wiithon import BinaryReader
from wiithon.crypto.layout import GROUP_SIZE


class WiaRawData:
    """
    Disc data outside any partition, stored as is
    """

    def __init__(self) -> None:
        """
        Constructor
        """
        #: The offset on the disc at which this data starts
        self.offset: int = 0

        #: Number of bytes covered by this struct
        self.size: int = 0

        #: Index of the first group holding this data, the other follows
        self.group_index: int = 0

        #: The number of group structs used for this data
        self.group_count: int = 0


    @classmethod
    def read(cls, stream: BinaryIO) -> "WiaRawData":
        """
        Read the raw data from the stream

        Args:
            stream: Current stream of the file

        Returns:
            WiaRawData constructed object
        """
        obj = cls()
        reader = BinaryReader(stream)

        offset          = reader.u64()
        size            = reader.u64()
        obj.group_index = reader.u32()
        obj.group_count = reader.u32()

        obj.offset = offset - (offset % GROUP_SIZE)
        obj.size   = size + (offset - obj.offset)

        return obj