import struct
from typing import BinaryIO

from wiithon.binary.reader import read_u32_shifted, read_u32
from wiithon.disc.enums import WiiPartType
from wiithon.disc.layout import PARTITION_TABLE_OFFSET, PARTITION_GROUP_COUNT


class WiiPartitionEntry:
    """
    Entry in the Wii partition table.
    https://wiibrew.org/wiki/Wii_disc#Partitions_information
    """

    def __init__(self, offset: int, part_type: int) -> None:
        self.offset: int = offset       # Partition offset (shifted)
        self.part_type: int = part_type    # WiiPartType (DATA=0, UPDATE=1, CHANNEL=2)

    @classmethod
    def read(cls, stream: BinaryIO) -> "WiiPartitionEntry":
        obj = cls(0, 0)
        obj.offset = read_u32_shifted(stream)
        obj.part_type = read_u32(stream)
        return obj

    def write(self, stream: BinaryIO) -> None:
        stream.write(struct.pack('>I', self.offset >> 2))
        stream.write(struct.pack('>I', self.part_type))

    def __repr__(self):
        return f"WiiPartitionEntry(Offset: {self.offset:X}, Partition_type: {self.part_type})"

    def get_readable_part_type(self) -> str:
        try:
            return WiiPartType(self.part_type).name.lower()
        except ValueError:
            return f"unknown ({self.part_type:#x})"


def read_parts(stream: BinaryIO) -> list[WiiPartitionEntry]:
    """
    Read the partition table from a Wii disc.

    The table is located at offset 0x40000 and contains up to 4 groups.
    Each group has a count + offset to its entries.
    :param stream:
    :return:
    """
    stream.seek(PARTITION_TABLE_OFFSET)

    groups: list[tuple[int, int]] = []
    for _ in range(PARTITION_GROUP_COUNT):
        count = read_u32(stream)
        offset = read_u32_shifted(stream)
        groups.append((count, offset))

    entries: list[WiiPartitionEntry] = []
    for count, offset in groups:
        if count == 0:
            continue
        stream.seek(offset)
        for _ in range(count):
            entries.append(WiiPartitionEntry.read(stream))

    return entries
