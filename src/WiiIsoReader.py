from io import BytesIO
from typing import BinaryIO, List, Optional

from WiiPartitionInfo import WiiPartitionInfo
from crypto.CryptPartReader import CryptPartReader
from file_system_table.FST import FST
from structs.Certificate import Certificate
from structs.DiscHeader import DiscHeader
from structs.TMD import TMD
from structs.WiiPartitionEntry import WiiPartitionEntry, read_parts
from structs.WiiPartitionHeader import WiiPartitionHeader


class WiiIsoReader:
    def __init__(self, path: str) -> None:
        self.file: BinaryIO = open(path, "rb")
        self.disc_header: DiscHeader = DiscHeader.read(self.file)
        self.partitions: List[WiiPartitionEntry] = read_parts(self.file)
        self.region: bytes = self.read_region()

    def get_data_partition(self) -> Optional[WiiPartitionEntry]:
        return next((p for p in self.partitions if p.part_type == 0), None)

    def update_data_partition(self) -> Optional[WiiPartitionEntry]:
        return next((p for p in self.partitions if p.part_type == 1), None)


    def read_region(self) -> bytes:
        self.file.seek(0x4E000)
        return self.file.read(0x20)

    def open_partition(self, entry: WiiPartitionEntry) -> WiiPartitionInfo:
        offset = entry.offset

        # Reading partition header
        self.file.seek(offset)
        header = WiiPartitionHeader.read(self.file)

        # Reading TMD
        self.file.seek(offset + header.tmd_offset)
        tmd = TMD.read(self.file)

        # Reading certificates
        self.file.seek(offset + header.certificate_chain_offset)
        certificates: List[Certificate] = []
        for _ in range(3):
            certificates.append(Certificate.read(self.file))

        # Crypto header for decrypted data
        data_offset = offset + header.data_offset
        title_key = header.ticket.title_key
        crypto = CryptPartReader(self.file, data_offset, title_key)

        # Disc Header
        boot_data = crypto.read_at(0, 0x440)
        internal_header = DiscHeader.read(BytesIO(boot_data))

        # FST
        fst_data = crypto.read_at(internal_header.FST_offset, internal_header.FST_size)
        dst = FST.read(BytesIO(fst_data), offset = 0)

        return WiiPartitionInfo(
            header=header, tmd=tmd, certificates=certificates,
            internal_header=internal_header, fst=dst,
            crypto=crypto, partition_offset=offset
        )

    def close(self) -> None:
        self.file.close()

    def __enter__(self) -> "WiiIsoReader":
        return self

    def __exit__(self, *args) -> None:
        self.close()