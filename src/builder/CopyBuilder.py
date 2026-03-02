import copy
from typing import Callable, List, Optional

from WiiIsoReader import WiiIsoReader
from builder.WiiPartitionInterface import WiiPartitionInterface
from crypto.CryptPartWriter import CryptPartWriter
from file_system_table.FST import FST
from file_system_table.FSTNode import FSTNode, FSTFile
from file_system_table.FSTToBytes import FSTToBytes
from helpers.Enums import WiiPartType
from structs.Certificate import Certificate
from structs.DiscHeader import DiscHeader
from structs.TMD import TMD
from structs.WiiPartitionEntry import WiiPartitionEntry
from structs.WiiPartitionHeader import WiiPartitionHeader


class CopyBuilder(WiiPartitionInterface):
    def __init__(self, reader: WiiIsoReader, partition: WiiPartitionEntry, fst_modifier: Optional[Callable[[FST], None]] = None) -> None:
        copy_partition = copy.copy(partition)
        self.partition_info = reader.open_partition(copy_partition)
        self.partition_type = partition.part_type
        self.header = self.partition_info.header
        self.bi2 = self.partition_info.read_bi2()
        self.apploader = self.partition_info.read_apploader()
        self.dol = self.partition_info.read_dol()
        self.tmd = self.partition_info.tmd
        self.certificates = self.partition_info.certificates
        self.fst = copy.copy(self.partition_info.fst)
        self.encrypted_header = self.partition_info.internal_header

        if not fst_modifier is None:
            fst_modifier(self.fst)

        self.fst_to_bytes = FSTToBytes(self.fst.entries)

    def get_partition_type(self) -> WiiPartType:
        return WiiPartType(self.partition_type)

    def get_header(self) -> WiiPartitionHeader:
        return self.header

    def get_tmd(self) -> TMD:
        return self.tmd

    def get_certificates(self) -> List[Certificate]:
        return self.certificates

    def get_encrypted_header(self) -> DiscHeader:
        return self.encrypted_header

    def get_bi2(self) -> bytes:
        return self.bi2

    def get_apploader(self) -> bytes:
        return self.apploader

    def get_dol(self) -> bytes:
        return self.dol

    def get_fst_to_bytes(self) -> FSTToBytes:
        return self.fst_to_bytes

    def write_file_data(self, writer: CryptPartWriter, progress_cb: Callable) -> int:
        total_file_count = self.fst_to_bytes.get_total_file_count()
        file_count = 0
        files: List[FSTFile] = []
        self.fst_to_bytes.callback_all_files(lambda _, curr: files.append(curr))

        for node in files:
            if node.length > 0:
                current_pos = writer.current_position

                aligned_pos = (current_pos + 31) & ~31
                original_offset = node.offset
                node.offset = aligned_pos

                writer.seek(node.offset)

                data = self.partition_info.crypto.read_at(original_offset, node.length)
                writer.write(data)

            file_count += 1
            if total_file_count > 0 and progress_cb is not None:
                progress_cb(file_count * 100 / total_file_count)

        return file_count