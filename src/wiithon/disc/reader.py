from io import BytesIO
from typing import BinaryIO, List, Optional

from wiithon.disc.WiiPartitionInfo import WiiPartitionInfo
from wiithon.crypto.CryptPartReader import CryptPartReader
from wiithon.file_system_table.FST import FST
from wiithon.binary.Utils import read_u32, json_repr
from wiithon.disc.structs.Certificate import Certificate
from wiithon.disc.structs.DiscHeader import DiscHeader
from wiithon.disc.structs.TMD import TMD
from wiithon.disc.structs.WiiPartitionEntry import WiiPartitionEntry, read_parts
from wiithon.disc.structs.WiiPartitionHeader import WiiPartitionHeader


@json_repr
class WiiIsoReader:
    def __init__(self, path: str) -> None:
        self.path = path
        self.file: BinaryIO = open(path, "rb")
        try:
            self.disc_header: DiscHeader = DiscHeader.read(self.file)
            self.partitions: List[WiiPartitionEntry] = read_parts(self.file)
            self.region: bytes = self.read_region()
            self.magic_word: int = self.read_magic_word()
            if self.magic_word != 0xC3F81A8E:
                raise ValueError(f"magic word is not 0xC3F81A8E: {self.magic_word}")
        except BaseException:
            self.file.close()
            raise

    def get_data_partition(self) -> Optional[WiiPartitionEntry]:
        return next((p for p in self.partitions if p.part_type == 0), None)

    def get_update_partition(self) -> Optional[WiiPartitionEntry]:
        return next((p for p in self.partitions if p.part_type == 1), None)

    def get_partitions(self) -> List[WiiPartitionEntry]:
        return self.partitions

    def read_region(self) -> bytes:
        self.file.seek(0x4E000)
        return self.file.read(0x20)

    def read_magic_word(self) -> int:
        self.file.seek(0x4FFFC)
        return read_u32(self.file)


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