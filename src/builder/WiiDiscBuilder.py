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
    """Écrit des zéros jusqu'à ce que writer.current_position == target."""
    delta = target - writer.current_position
    if delta < 0:
        raise ValueError(f"Déjà à 0x{writer.current_position:X}, target=0x{target:X}")
    if delta > 0:
        writer.write(bytes(delta))


class WiiDiscBuilder:
    def __init__(self, disc_header: DiscHeader, region: bytes) -> None:
        self.disc_header = disc_header
        self.region = region                          # 32 bytes de 0x4E000
        self._partitions: list[tuple[WiiPartitionEntry, int]] = []

    def add_partition(self, dest: BinaryIO, partition_def, progress_cb=None) -> int:
        # Calcul de l'offset de partition
        if not self._partitions:
            offset = 0xF800000
        else:
            last_entry, last_data_size = self._partitions[-1]
            offset = _align_up(last_entry.offset + 0x20000 + last_data_size, GROUP_SIZE)

        import copy
        header = copy.copy(partition_def.get_header())
        internal_header = copy.copy(partition_def.get_internal_header())
        fst_to_bytes    = partition_def.get_fst_to_bytes()

        # Pré-calcul des offsets fichiers dans la FST
        fst_offset      = internal_header.FST_offset
        file_data_start = fst_offset + fst_to_bytes.byte_size()
        partition_def.assign_file_offsets(file_data_start)

        # Mise à jour FST_size dans le boot.bin
        internal_header.FST_size     = fst_to_bytes.byte_size()
        internal_header.FST_max_size = fst_to_bytes.byte_size()

        # Écriture en-tête partition (data_size = 0 placeholder)
        dest.seek(offset)
        header.data_size = 0
        header.write(dest)

        dest.seek(offset + header.tmd_offset)
        partition_def.get_tmd().write(dest)

        dest.seek(offset + header.certificate_chain_offset)
        for cert in partition_def.get_certificates():
            cert.write(dest)

        # Zone de données chiffrée
        data_offset = offset + header.data_offset
        writer      = CryptPartWriter(dest, data_offset, header.ticket.title_key)

        # boot.bin → 0x000 (exactement 0x440 octets)
        boot_buf = BytesIO()
        internal_header.write(boot_buf)
        writer.write(boot_buf.getvalue())

        # bi2 → 0x440 (exactement 0x2000 octets)
        writer.write(partition_def.get_bi2())

        # apploader → 0x2440
        writer.write(partition_def.get_apploader())

        # DOL → pad jusqu'à DOL_offset, puis écriture
        _pad_to(writer, internal_header.DOL_offset)
        writer.write(partition_def.get_dol())

        # FST → pad jusqu'à FST_offset, puis sérialisation
        _pad_to(writer, fst_offset)
        fst_buf = BytesIO()
        fst_to_bytes.write_to(fst_buf)
        writer.write(fst_buf.getvalue())

        # Données fichiers
        file_count = partition_def.write_file_data(writer, progress_cb)

        writer.close()  # flush du dernier groupe

        # H3 table
        dest.seek(offset + header.global_hash_table_offset)
        dest.write(writer.get_h3_table())

        # data_size réel + réécriture du header
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
        dest.write(struct.pack('>I', len(self._partitions)))  # count groupe 0
        dest.write(struct.pack('>I', 0x40020 >> 2))           # offset entrées (shifté)
        dest.write(b'\x00' * 24)                              # groupes 1–3 vides

        dest.seek(0x40020)
        for entry, _ in self._partitions:
            entry.write(dest)
