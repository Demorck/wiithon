import struct
import hashlib
from io import BytesIO
from typing import List, BinaryIO, Callable, Optional

from builder.WiiPartitionInterface import WiiPartitionInterface
from crypto.CryptPartWriter import CryptPartWriter
from file_system_table.FSTToBytes import FSTToBytes
from file_system_table.FSTNode import FSTFile
from helpers.Constants import GROUP_SIZE, GROUP_DATA_SIZE
from structs.DiscHeader import DiscHeader
from structs.WiiPartitionEntry import WiiPartitionEntry
from structs.WiiPartitionHeader import WiiPartitionHeader

def align_next(num: int, alignment: int) -> int:
    return (num + alignment - 1) & ~(alignment - 1)

class WiiDiscBuilder:
    def __init__(self, header: DiscHeader, region: bytes):
        self.header: DiscHeader = header
        self.region: bytes = region
        self.partitions: List[tuple] = []
        self.current_data_offset = 0x50000

    def add_partition(self, stream: BinaryIO, new_partition: WiiPartitionInterface, progress_cb: Optional[Callable]) -> None:
        """
        TODO: 160 lines long for this function so refactor it maybe
        :param stream:
        :param new_partition:
        :param progress_cb:
        :return:
        """
        if progress_cb:
            progress_cb(0)
            
        part_data_off = self.current_data_offset
        self.partitions.append((WiiPartitionEntry(part_data_off, new_partition.get_partition_type()), part_data_off, 0))

        # Build placeholder headers
        part_header = WiiPartitionHeader()
        part_header.ticket = new_partition.get_ticket()
        part_header.tmd_offset = 0x2C0
        
        tmd_buffer = BytesIO()
        new_partition.get_tmd().write(tmd_buffer)
        tmd_bytes = bytearray(tmd_buffer.getvalue())
        part_header.tmd_size = len(tmd_bytes)
        
        part_header.certificate_chain_offset = align_next(part_header.tmd_offset + part_header.tmd_size, 0x20)
        
        # Write cert chain
        stream.seek(part_data_off + part_header.certificate_chain_offset)
        cert_start = stream.tell()
        for i in range(len(new_partition.get_certificates())):
            new_partition.get_certificates()[i].write(stream)
        part_header.certificate_chain_size = stream.tell() - cert_start

        # Open encrypted writer at 0x20000 relative to part_data_off
        crypt_start = part_data_off + 0x20000
        crypt_writer = CryptPartWriter(stream, crypt_start, part_header.ticket.title_key)
        
        source_fst = new_partition.get_fst()
        files = []
        total_bytes = 0
        
        def collect_files(paths, node):
            files.append((paths, node))
            if isinstance(node, FSTFile):
                nonlocal total_bytes
                total_bytes += node.length
        
        # FSTToBytes to iterate
        fst_to_bytes = FSTToBytes(source_fst.entries)
        fst_to_bytes.callback_all_files(collect_files)
        total_files = len(files)
        uses_file_byte_progress = total_bytes > 0
        
        part_disc_header = new_partition.get_encrypted_header()
        
        # BI2 and Apploader
        crypt_writer.seek(0x440)
        crypt_writer.write(new_partition.get_bi2())
        crypt_writer.seek(0x2440)
        crypt_writer.write(new_partition.get_apploader())
        
        # DOL
        part_disc_header.DOL_offset = align_next(crypt_writer.current_position, 0x20)
        crypt_writer.seek(part_disc_header.DOL_offset)
        crypt_writer.write(new_partition.get_dol())
        
        # Write FST
        part_disc_header.FST_offset = align_next(crypt_writer.current_position, 0x20)
        crypt_writer.seek(part_disc_header.FST_offset)
        fst_to_bytes.write_to(crypt_writer)

        # Padding
        crypt_writer.write(b'\x00' * 4)
        fst_end = crypt_writer.current_position
        part_disc_header.FST_size = fst_end - part_disc_header.FST_offset
        part_disc_header.FST_max_size = part_disc_header.FST_size

        # Write data
        data_start = align_next(crypt_writer.current_position, 0x40)
        crypt_writer.seek(data_start)
        processed_files = 0
        processed_file_bytes = 0

        for paths, node in files:
            processed_files += 1
            node.offset = crypt_writer.current_position
            
            full_path = paths + [node.name]
            file_data = new_partition.get_file_data(full_path)
            
            node.length = len(file_data)
            
            # Write data
            bytes_to_write = len(file_data)
            crypt_writer.write(file_data)
            
            if uses_file_byte_progress and progress_cb:
                processed_file_bytes += bytes_to_write
                progress_cb(int((processed_file_bytes / total_bytes) * 100))
                
            # Align next to 0x40 with 0
            current_position = crypt_writer.current_position
            next_start = align_next(current_position, 0x40)
            if next_start > current_position:
                crypt_writer.write(b'\x00' * (next_start - current_position))
                
            if not uses_file_byte_progress and progress_cb:
                progress_cb(int((processed_files / total_files) * 100))

        # Align total size to next full group
        groups = (crypt_writer.current_position + GROUP_DATA_SIZE - 1) // GROUP_DATA_SIZE
        total_size = groups * GROUP_DATA_SIZE
        total_encrypted_size = groups * GROUP_SIZE
        
        self.current_data_offset += 0x20000 + total_encrypted_size
        
        # Rewrite FST according to offset of datas
        crypt_writer.seek(part_disc_header.FST_offset)
        fst_to_bytes.write_to(crypt_writer)
        
        # Write partition disc header
        crypt_writer.seek(0)
        part_disc_header.write(crypt_writer)
        
        crypt_writer.close()
        h3 = crypt_writer.get_h3_table()
        
        # Write h3
        stream.seek(part_data_off + 0x8000)
        stream.write(h3)
        
        part_header.global_hash_table_offset = 0x8000
        part_header.data_offset = 0x20000
        part_header.data_size = total_size
        
        # TMD hash and signature (signature is not correct says Dolphin but who cares)
        hasher = hashlib.sha1()
        hasher.update(h3)
        digest = hasher.digest()
        
        tmd_bytes[0x1F4:0x1F4+20] = digest
        tmd_bytes[0x1EC:0x1EC+8] = struct.pack(">Q", total_size)
        
        # Just 0
        tmd_bytes[4:0x104] = b'\x00' * 0x100
        
        # Brute force starting hash to \x00
        for i in range(0xFFFFFFFFFFFFFFFF):
            tmd_bytes[0x19A:0x19A+8] = struct.pack("=Q", i) 
            temp_hasher = hashlib.sha1()
            temp_hasher.update(tmd_bytes[0x140:])
            hash_res = temp_hasher.digest()
            if hash_res[0] == 0:
                break
                
        stream.seek(part_data_off + part_header.tmd_offset)
        stream.write(tmd_bytes)
        
        stream.seek(part_data_off)
        part_header.write(stream)


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
