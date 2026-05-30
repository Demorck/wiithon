import copy
import os

from typing import Callable, List, Optional

from wiithon.structs.Certificate import Certificate
from wiithon.structs.DiscHeader import DiscHeader
from wiithon.structs.TMD import TMD
from wiithon.structs.Ticket import Ticket
from wiithon.structs.WiiPartitionEntry import WiiPartitionEntry
from wiithon.helpers.Enums import WiiPartType
from wiithon.file_helper.dol import DOL

from wiithon.WiiIsoReader import WiiIsoReader
from wiithon.builder.WiiPartitionInterface import WiiPartitionInterface
from wiithon.file_system_table.FST import FST


class CopyBuilder(WiiPartitionInterface):
    def __init__(self, reader: WiiIsoReader, partition: WiiPartitionEntry,
                 fst_modifier: Optional[Callable[[FST], None]] = None,
                 dol_modifier: Optional[Callable[[DOL], None]] = None,
                 file_overrides: dict[str, bytes] | None = None) -> None:
        copy_partition = copy.copy(partition)
        self.partition_info = reader.open_partition(copy_partition)
        self.partition_type = partition.part_type
        self.bi2 = self.partition_info.read_bi2()
        self.apploader = self.partition_info.read_apploader()
        self.dol = self.partition_info.read_dol()
        self.tmd = self.partition_info.tmd
        self.certificates = self.partition_info.certificates
        self.fst = copy.copy(self.partition_info.fst)
        self.encrypted_header = self.partition_info.internal_header
        self.ticket = self.partition_info.header.ticket

        if fst_modifier is not None:
            fst_modifier(self.fst)

        if dol_modifier is not None:
            dol_modifier(self.dol)

        self._file_overrides: dict[str, bytes] = file_overrides or {}

    def get_partition_type(self) -> WiiPartType:
        return WiiPartType(self.partition_type)

    def get_ticket(self) -> Ticket:
        return self.ticket

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
        return self.dol.to_bytes()

    def get_fst(self) -> FST:
        return self.fst

    def get_file_data(self, path: List[str]) -> bytes:
        key = "/".join(path)
        if key in self._file_overrides:
            return self._file_overrides[key]

        node = self.fst.find_node(os.path.join(*path) if path else "")
            
        if node and not hasattr(node, "children"): # ie: is a file
            data = self.partition_info.crypto.read_at(node.original_offset, node.length)
            return data

        raise FileNotFoundError(f"File not found in FST: {path}")
