import copy
import os

from typing import Callable, List, Optional

from structs.Certificate import Certificate
from structs.DiscHeader import DiscHeader
from structs.TMD import TMD
from structs.Ticket import Ticket
from structs.WiiPartitionEntry import WiiPartitionEntry
from helpers.Enums import WiiPartType

from WiiIsoReader import WiiIsoReader
from builder.WiiPartitionInterface import WiiPartitionInterface
from file_system_table.FST import FST


class CopyBuilder(WiiPartitionInterface):
    def __init__(self, reader: WiiIsoReader, partition: WiiPartitionEntry, fst_modifier: Optional[Callable[[FST], None]] = None) -> None:
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
        return self.dol

    def get_fst(self) -> FST:
        return self.fst

    def get_file_data(self, path: List[str]) -> bytes:
        node = self.fst.find_node(os.path.join(*path) if path else "")
        if not node:
             current = self.fst.entries
             found = False
             target = None
             for part in path:
                 found = False
                 for entry in current:
                     if entry.name == part:
                         target = entry
                         if hasattr(entry, 'children'):
                             current = entry.children
                         found = True
                         break
                 if not found:
                     break
             node = target if found else None
            
        if node and not hasattr(node, "children"): # ie: is a file
            data = self.partition_info.crypto.read_at(node.original_offset, node.length)
            return data

        raise FileNotFoundError(f"File not found in FST: {path}")
