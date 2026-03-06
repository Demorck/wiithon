import os
from typing import Callable, List, BinaryIO

from WiiIsoReader import WiiIsoReader
from builder.WiiPartitionInterface import WiiPartitionInterface
from crypto.CryptPartWriter import CryptPartWriter
from file_system_table.FST import FST
from file_system_table.FSTNode import FSTFile
from file_system_table.FSTToBytes import FSTToBytes
from helpers.Enums import WiiPartType
from structs.Certificate import Certificate
from structs.DiscHeader import DiscHeader
from structs.TMD import TMD
from structs.WiiPartitionEntry import WiiPartitionEntry
from structs.WiiPartitionHeader import WiiPartitionHeader


def build_from_directory_tree(files_dir: str) -> FST:
    fst = FST()
    dirs = []
    build_from_directory_tree_recursive(files_dir, dirs, fst)
    return fst

def build_from_directory_tree_recursive(path: str, dirs: List[str], fst: FST) -> None:
    for entry in os.scandir(path):
        filename = entry.name
        if entry.is_dir():
            dirs.append(filename)
            build_from_directory_tree_recursive(entry.path, dirs, fst)
            dirs.pop()
        else:
            fst_file = FSTFile(filename, 0, os.stat(entry).st_size)
            fst.entries.append(fst_file)

class DirectoryPartitionBuilder(WiiPartitionInterface):
    def __init__(self, path: str, partition_type: WiiPartType)-> None:
        sys_folder = path + "/sys"
        files_dir = path + "/files"
        with open(sys_folder + "/boot.bin", 'rb') as f:
            self.encrypted_header = DiscHeader.read(f)

        with open(sys_folder + "/bi2.bin", 'rb') as f:
            self.bi2 = f.read()

        with open(sys_folder + "/apploader.img", 'rb') as f:
            self.apploader = f.read()

        with open(sys_folder + "/main.dol", 'rb') as f:
            self.dol = f.read()

        # with open(path + "/header.bin", 'rb') as f:
        #     self.header = WiiPartitionHeader.read(f)
        #

        with open(path + "/tmd.bin", 'rb') as f:
            self.tmd = TMD.read(f)

        with open(path + "/cert.bin", 'rb') as f:
            self.certificates = []
            for _ in range(3):
                self.certificates.append(Certificate.read(f))

        self.fst = build_from_directory_tree(files_dir)
        self.fst_to_bytes = FSTToBytes(self.fst.entries)
        self.partition_type = partition_type

    def get_partition_type(self) -> WiiPartType:
        return self.partition_type

    def get_header(self) -> WiiPartitionHeader:
        return self.header

    def get_tmd(self) -> TMD:
        pass

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
        pass