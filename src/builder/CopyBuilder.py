import copy
from typing import Callable, List, Optional

from WiiIsoReader import WiiIsoReader
from builder.WiiPartitionInterface import WiiPartitionInterface
from crypto.CryptPartWriter import CryptPartWriter
from file_system_table.FST import FST
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
        partition_info = reader.open_partition(copy_partition)
        self.partition_type = partition.part_type
        self.header = partition_info.header
        self.bi2 = partition_info.read_bi2()
        self.apploader = partition_info.read_apploader()
        self.dol = partition_info.read_dol()
        self.tmd = partition_info.tmd
        self.certificates = partition_info.certificates
        self.fst = copy.copy(partition_info.fst)
        self.encrypted_header = partition_info.internal_header

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

    def write_file_data(self, writer: CryptPartWriter, progress_cb: Callable) -> FSTToBytes:
        pass