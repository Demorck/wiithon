from typing import BinaryIO

from wiithon.binary.reader import BinaryReader
from wiithon.rvz.layout import PARTITION_SEGMENT, PARTITION_TITLE_KEY_SIZE
from wiithon.rvz.structs.partition_data import WiaPartitionData


class WiaPartition:
    """
    Encrypted and hashed partition data
    """
    def __init__(self):
        """
        Constructor
        """
        #: Title key for this partition, decrypted
        self.title_key: bytes = b"\x00" * PARTITION_TITLE_KEY_SIZE

        #: The two segments this partition is split to
        self.segments: list[WiaPartitionData] = []

    @classmethod
    def read(cls, stream: BinaryIO) -> "WiaPartition":
        """
        Read partition from stream

        Args:
            stream: The stream to read from

        Returns:
            The constructed WiaPartition
        """
        obj = cls()
        reader = BinaryReader(stream)

        obj.title_key = reader.raw(PARTITION_TITLE_KEY_SIZE)
        obj.segments = [WiaPartitionData.read(stream) for _ in range(PARTITION_SEGMENT)]

        return obj