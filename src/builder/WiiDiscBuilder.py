import struct
from io import BytesIO
from typing import BinaryIO

from crypto.CryptPartWriter import CryptPartWriter
from helpers.Constants import GROUP_SIZE, GROUP_DATA_SIZE
from structs.DiscHeader import DiscHeader
from structs.WiiPartitionEntry import WiiPartitionEntry


def _align_up(value: int, alignment: int) -> int:
    return ((value + alignment - 1) // alignment) * alignment

def _pad_to(writer: CryptPartWriter, target: int) -> None:
    """Padding zeros writer.current_position == target"""
    delta = target - writer.current_position
    if delta < 0:
        raise ValueError(f"Already at 0x{writer.current_position:X}, target=0x{target:X}")
    if delta > 0:
        writer.write(bytes(delta))


class WiiDiscBuilder:
    def __init__(self, disc_header: DiscHeader, region: bytes) -> None:
        self.disc_header = disc_header
        self.region = region                          # 32 bytes de 0x4E000
        self._partitions: list[tuple[WiiPartitionEntry, int]] = []

    def add_partition(self, dest: BinaryIO, partition_def, progress_cb=None) -> int:
        if not self._partitions:
            offset = 0xF800000
        else:
            last_entry, last_data_size = self._partitions[-1]
            offset = _align_up(last_entry.offset + 0x20000 + last_data_size, GROUP_SIZE)

        import copy
        header = copy.copy(partition_def.get_header())
        internal_header = copy.copy(partition_def.get_internal_header())
        fst_to_bytes    = partition_def.get_fst_to_bytes()

        # FST
        fst_offset      = internal_header.FST_offset
        fst_size_padded = (fst_to_bytes.byte_size() + 3) & ~3
        file_data_start = fst_offset + fst_size_padded
        partition_def.assign_file_offsets(file_data_start)
        internal_header.FST_size     = fst_to_bytes.byte_size()
        internal_header.FST_max_size = fst_to_bytes.byte_size()

        # Header
        dest.seek(offset)
        header.data_size = 0
        header.write(dest)

        dest.seek(offset + header.tmd_offset)
        partition_def.get_tmd().write(dest)

        dest.seek(offset + header.certificate_chain_offset)
        for cert in partition_def.get_certificates():
            cert.write(dest)

        # Data
        data_offset = offset + header.data_offset
        writer      = CryptPartWriter(dest, data_offset, header.ticket.title_key)

        # boot.bin
        boot_buf = BytesIO()
        internal_header.write(boot_buf)
        writer.write(boot_buf.getvalue())

        # bi2
        writer.write(partition_def.get_bi2())

        # apploader
        writer.write(partition_def.get_apploader())

        # DOL
        _pad_to(writer, internal_header.DOL_offset)
        writer.write(partition_def.get_dol())

        # FST
        _pad_to(writer, fst_offset)
        fst_buf = BytesIO()
        fst_to_bytes.write_to(fst_buf)
        writer.write(fst_buf.getvalue())
        _pad_to(writer, file_data_start)

        file_count = partition_def.write_file_data(writer, progress_cb)

        writer.close()

        # H3
        dest.seek(offset + header.global_hash_table_offset)
        dest.write(writer.get_h3_table())

        # data_size + header
        data_size = ((writer.current_position // GROUP_DATA_SIZE) + 1) * GROUP_SIZE
        dest.seek(offset)
        header.data_size = data_size
        header.write(dest)

        entry          = WiiPartitionEntry()
        entry.offset   = offset
        entry.part_type = partition_def.get_part_type()
        self._partitions.append((entry, data_size))
        return file_count

    def finish(self, dest: BinaryIO) -> None:
        dest.seek(0)
        self.disc_header.write(dest)

        dest.seek(0x4E000)
        dest.write(self.region)

        dest.seek(0x40000)
        dest.write(struct.pack('>I', len(self._partitions)))
        dest.write(struct.pack('>I', 0x40020 >> 2))
        dest.write(b'\x00' * 24)

        dest.seek(0x40020)
        for entry, _ in self._partitions:
            entry.write(dest)
