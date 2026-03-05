import copy
import struct

from typing import List, BinaryIO, Callable, Optional

from builder.WiiPartitionInterface import WiiPartitionInterface
from crypto.CryptPartWriter import CryptPartWriter
from helpers.Constants import GROUP_SIZE, GROUP_DATA_SIZE
from helpers.Enums import WiiPartType
from structs.DiscHeader import DiscHeader
from structs.WiiPartitionEntry import WiiPartitionEntry


class WiiDiscBuilder:
    def __init__(self, header: DiscHeader, region: bytes):
        self.header: DiscHeader = header
        self.region: bytes = region
        self.partitions: List[(WiiPartitionEntry, int, int)] = []


    def add_partition(self, stream: BinaryIO, new_partition: WiiPartitionInterface, progress_cb: Optional[Callable]) -> None:
        offset = 0xF800000 # 0x50000 First place after header so we can save some spaces ?

        # Nintendo seems to use these partitions for UPDATE & DATA for Super Mario Galaxy.
        if new_partition.get_partition_type() == WiiPartType.UPDATE:
            offset = 0x50000

        if new_partition.get_partition_type() == WiiPartType.DATA:
            offset = 0xF800000

        # if self.partitions:
        #     last_partition_entry, data_size, _ = self.partitions[-1]
        #     data_offset = last_partition_entry.offset + 0x20000
        #     offset = ((data_offset + data_size + (GROUP_SIZE - 1)) // GROUP_SIZE) * GROUP_SIZE

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

        data_offset = offset + wii_partition_header.data_offset
        crypt_writer = CryptPartWriter(stream, data_offset, wii_partition_header.ticket.title_key)
        crypt_writer.seek(0)
        crypt_writer.write(new_partition.get_encrypted_header().get_bytes())
        crypt_writer.seek(0x440)
        crypt_writer.write(new_partition.get_bi2())
        crypt_writer.seek(0x2440)
        crypt_writer.write(new_partition.get_apploader())
        dol_offset = new_partition.get_encrypted_header().DOL_offset
        crypt_writer.seek(dol_offset)
        crypt_writer.write(new_partition.get_dol())

        fst_to_bytes = new_partition.get_fst_to_bytes()
        fst_offset = new_partition.get_encrypted_header().FST_offset
        actual_fst_size = fst_to_bytes.byte_size()
        crypt_writer.seek(fst_offset)

        fst_to_bytes.write_to(crypt_writer)
        new_partition.get_encrypted_header().FST_size = actual_fst_size
        file_count = new_partition.write_file_data(crypt_writer, progress_cb)

        crypt_writer.close()
        h3 = crypt_writer.get_h3_table()
        h3_offset_in_part = wii_partition_header.global_hash_table_offset
        stream.seek(offset + h3_offset_in_part)
        stream.write(h3)

        end_pos = crypt_writer.current_position
        num_groups = (end_pos + GROUP_DATA_SIZE - 1) // GROUP_DATA_SIZE
        data_size = num_groups * GROUP_SIZE

        stream.seek(offset)
        new_wii_partition_header = copy.copy(wii_partition_header)
        new_wii_partition_header.data_size = data_size
        new_wii_partition_header.write(stream)

        wii_part = WiiPartitionEntry(offset, new_partition.get_partition_type())
        self.partitions.append((wii_part, data_offset, file_count))



    def finish(self, stream: BinaryIO) -> None:
        stream.seek(0)
        self.header.write(stream)
        stream.seek(0x40000)
        stream.write(struct.pack(">I", len(self.partitions)))
        stream.write(struct.pack(">I", 0x40020 >> 2))
        stream.write(b"\x00" * 24)
        stream.seek(0x40020)
        for partition_entry, _, _ in self.partitions:
            partition_entry.write(stream)

        stream.seek(0x4E000)
        stream.write(self.region)

        stream.seek(0x4FFFC)
        stream.write(struct.pack(">I", 0xC3F81A8E))

        # TESTED