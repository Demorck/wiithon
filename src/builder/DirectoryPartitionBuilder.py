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


from file_system_table.FSTNode import FSTFile, FSTDirectory

def build_from_directory_tree(files_dir: str) -> FST:
    fst = FST()
    _build_from_directory_tree_recursive(files_dir, fst.entries)
    return fst

def _build_from_directory_tree_recursive(path: str, current_entries: list) -> None:
    # Ordered
    entries = sorted(os.scandir(path), key=lambda e: e.name.lower())
    for entry in entries:
        filename = entry.name
        if entry.is_dir():
            fst_dir = FSTDirectory(filename)
            current_entries.append(fst_dir)
            _build_from_directory_tree_recursive(entry.path, fst_dir.children)
        else:
            fst_file = FSTFile(filename, 0, os.stat(entry).st_size)
            current_entries.append(fst_file)

class DirectoryPartitionBuilder(WiiPartitionInterface):
    def __init__(self, path: str, partition_type: WiiPartType)-> None:
        sys_folder = path + "/sys"
        self.files_dir = path + "/files"
        with open(sys_folder + "/boot.bin", 'rb') as f:
            self.encrypted_header = DiscHeader.read(f)

        with open(sys_folder + "/bi2.bin", 'rb') as f:
            self.bi2 = f.read()

        with open(sys_folder + "/apploader.img", 'rb') as f:
            self.apploader = f.read()

        with open(sys_folder + "/main.dol", 'rb') as f:
            self.dol = f.read()

        with open(path + "/header.bin", 'rb') as f:
            self.header = WiiPartitionHeader.read(f)

        with open(path + "/tmd.bin", 'rb') as f:
            self.tmd = TMD.read(f)

        with open(path + "/cert.bin", 'rb') as f:
            self.certificates = []
            for _ in range(3):
                self.certificates.append(Certificate.read(f))

        # For now
        self.region: bytes = b'\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x80\x06\x80\x80\x80\x80\x80\x80\x80\x80\x80\x80\x80\x80\x80\x80'

        self.fst = build_from_directory_tree(self.files_dir)
        self.fst_to_bytes = FSTToBytes(self.fst.entries)
        self.partition_type = partition_type

    def get_partition_type(self) -> WiiPartType:
        return self.partition_type

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

        fst_start_offset = writer.tell() - self.fst_to_bytes.byte_size()

        files = []
        self.fst_to_bytes.callback_all_files(lambda paths, curr: files.append((paths, curr)))
        buffer = bytearray()
        for paths, node in files:
            # Rebuild path
            rel_path = os.path.join(*(paths + [node.name]))
            file_path = os.path.join(self.files_dir, rel_path)
            
            with open(file_path, 'rb') as f:
                node.offset = writer.tell()
                data = f.read()
                node.length = len(data)
                writer.write(data)
                
            file_count += 1


            if total_file_count > 0 and progress_cb is not None:
                progress_cb(int(file_count * 100 / total_file_count))


        end_of_files_offset = writer.tell()
        writer.seek(fst_start_offset)
        self.fst_to_bytes.write_to(writer)
        writer.seek(end_of_files_offset)
        return file_count