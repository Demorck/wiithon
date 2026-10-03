import os

from wiithon import WiiPartitionInfo
from wiithon.crypto.layout import BLOCK_SIZE, GROUP_DATA_SIZE, BLOCK_PER_GROUP
from wiithon.disc.reader import WiiIsoReader
from wiithon.rvz.layout import DHEAD_SIZE
from wiithon.rvz.structs.partition import WiaPartition
from wiithon.rvz.structs.partition_data import WiaPartitionData
from wiithon.rvz.structs.raw_data import WiaRawData


class DiscPlan:
    """
    Where every byte of a disc goes once it is cut into chunks
    """

    def __init__(self) -> None:
        #: Size of the disc being described
        self.iso_size: int = 0

        #: The first 0x80 bytes
        self.disc_head: bytes = b''

        #: Size the chunks were cut at
        self.chunk_size: int = 0

        #: Areas living outside any partition in disc order
        self.raw_data: list[WiaRawData] = []

        #: Paritions in disc order
        self.partitions: list[WiaPartition] = []

        #: How many groups the whole disc have
        self.group_count: int = 0

class DiscPlanner:
    """
    Works out the descriptos a WIA / RVZ needs to describe a disc
    """

    def __init__(self, chunk_size: int) -> None:
        """
        Constructor

        Args:
            chunk_size: Size the data will be cut at
        """
        self.chunk_size = chunk_size
        self._plan = DiscPlan()
        self._next_group = 0

    def plan(self, reader: WiiIsoReader) -> DiscPlan:
        """
        Describe a disc

        Args:
            reader: An Open disc image

        Returns:
            Every descriptor the image will need
        """
        self._plan = DiscPlan()
        self._plan.chunk_size = self.chunk_size
        self._plan.iso_size = os.path.getsize(reader.path)
        reader.file.seek(0)
        self._plan.disc_head = reader.file.read(DHEAD_SIZE)
        self._next_group = 0
        cursor = 0
        
        for entry in sorted(reader.get_partitions(), key=lambda p: p.offset):
            info = reader.open_partition(entry)
            
            if entry.offset > cursor:
                self._add_raw(cursor, entry.offset - cursor)
                
            self._add_raw(entry.offset, info.header.data_offset)
            self._add_partition(entry.offset, info)
            cursor = entry.offset + info.header.data_offset + info.header.data_size

        if cursor < self._plan.iso_size:
            self._add_raw(cursor, self._plan.iso_size - cursor)

        self._plan.group_count = self._next_group

        return self._plan

    def _add_raw(self, offset: int, size: int) -> None:
        """
        Append one raw area and claim the groups it needs

        Args:
            offset: Where it starts on the disc
            size: How many bytes it covers
        """
        entry = WiaRawData()
        entry.offset = offset
        entry.size = size
        entry.first_group_index = self._next_group
        entry.group_count = self._groups_for(size)
        self._next_group += entry.group_count

        self._plan.raw_data.append(entry)

    def _add_partition(self, offset: int, info: WiiPartitionInfo) -> None:
        """
        Append one partition, split in two segments and claim their groups
        Args:
            offset: Where the partition starts on the disc
            info: The partition as the disc reader describes it
        """
        blocks = info.header.data_size // BLOCK_SIZE
        first_block = (offset + info.header.data_offset) // BLOCK_SIZE

        fst_end = info.internal_header.FST_offset + info.internal_header.FST_size
        groups = (fst_end + GROUP_DATA_SIZE - 1) // GROUP_DATA_SIZE
        management = min(groups * BLOCK_PER_GROUP, blocks)

        partition = WiaPartition()
        partition.title_key = info.header.ticket.title_key
        partition.segments = [
            self._segment(first_block, 0, management),
            self._segment(first_block, management, blocks - management),
        ]

        self._plan.partitions.append(partition)

    def _segment(self, first_block: int, start: int, count: int) -> WiaPartitionData:
        """
        Build one segment descriptor and claim the groups it needs

        Args:
            first_block: Disc block the partition data starts at
            start: Which of its blocks this segment starts at
            count: How many blocks it covers (none possible)

        Returns:
            The descriptor
        """
        segment = WiaPartitionData()
        segment.first_block = first_block + start
        segment.block_count = count
        segment.group_index = self._next_group
        segment.group_count = self._groups_for(count * BLOCK_SIZE) if count else 0
        self._next_group += segment.group_count

        return segment

    def _groups_for(self, size: int) -> int:
        """
        How many chunks it takes to cover a size

        Args:
            size: Bytes to cover

        Returns:
            The number of groups
        """
        return (size + self.chunk_size - 1) // self.chunk_size
            
    