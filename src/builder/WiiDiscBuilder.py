import copy
from typing import List, BinaryIO, Callable, Optional

from builder.WiiPartitionInterface import WiiPartitionInterface
from helpers.Constants import GROUP_SIZE
from structs.DiscHeader import DiscHeader
from structs.WiiPartitionEntry import WiiPartitionEntry


class WiiDiscBuilder:
    def __init__(self, header: DiscHeader, region: bytes):
        self.header: DiscHeader = header
        self.region: bytes = region
        self.partitions: List[(WiiPartitionEntry, int, int)] = []


    def add_partition(self, stream: BinaryIO, new_partition: WiiPartitionInterface, progress_cb: Optional[Callable]) -> None:
        offset = 0xF800000
        if self.partitions:
            last_partition_entry, data_size, _ = self.partitions[-1]
            data_offset = last_partition_entry.offset + 0x20000
            offset = ((data_offset + data_size + (GROUP_SIZE - 1)) // GROUP_SIZE) * GROUP_SIZE

        wii_partition_header = new_partition.get_header()
        stream.seek(offset)
        modified_header = copy.copy(wii_partition_header)
        modified_header.data = 0
        modified_header.write(stream)

        stream.seek(offset + wii_partition_header.tmd_offset)
        new_partition.get_tmd().write(stream)

        stream.seek(offset + wii_partition_header.certificate_chain_offset)
        for i in range(len(new_partition.get_certificates())):
            new_partition.get_certificates()[i].write(stream)

        ### TESTED ABOVE ###