from io import BytesIO
from typing import List, Optional

from crypto.CryptPartReader import CryptPartReader
from file_system_table.FST import FST
from file_system_table.FSTNode import FSTNode, FSTDirectory, FSTFile
from structs.ApploaderHeader import ApploaderHeader
from structs.Certificate import Certificate
from structs.DiscHeader import DiscHeader
from structs.TMD import TMD
from structs.WiiPartitionHeader import WiiPartitionHeader
from structs.DOLHeader import DOLHeader


class WiiPartitionInfo:
    def __init__(self,  header: WiiPartitionHeader, tmd: TMD,
                        certificates: List[Certificate], internal_header: DiscHeader,
                        fst: FST, crypto: CryptPartReader,
                        partition_offset: int) -> None:
        self.header = header
        self.tmd = tmd
        self.certificates = certificates
        self.internal_header = internal_header
        self.fst = fst
        self.crypto = crypto
        self.partition_offset = partition_offset

    def read_file(self, path: str) -> bytes:
        parts = path.strip("/").split('/')
        node: Optional[FSTNode] = None
        current_list = self.fst.entries

        for part in parts:
            node = None
            for child in current_list:
                if child.name == part:
                    node = child
                    break

            if node is None:
                raise FileNotFoundError(f"File not found: {path}")

            if isinstance(node, FSTDirectory):
                current_list = node.children

        if not isinstance(node, FSTFile):
            raise IsADirectoryError(f"Path is a directory: {path}")

        return self.crypto.read_at(node.offset, node.length)


    def read_apploader(self) -> bytes:
        apploader_offset = 0x2440 # maybe constant though
        header_data = self.crypto.read_at(apploader_offset, 0x20)
        apploader_header = ApploaderHeader.read(BytesIO(header_data))
        total_size = 0x20 + apploader_header.size1 + apploader_header.size2

        return self.crypto.read_at(apploader_offset, total_size)

    def read_dol(self) -> bytes:
        dol_offset = self.internal_header.DOL_offset
        header_data = self.crypto.read_at(dol_offset, 0x100)
        dol_header = DOLHeader.read(BytesIO(header_data))

        dol_size = 0x100
        for i in range(7):
            end = dol_header.text_offset[i] + dol_header.text_length[i]
            dol_size = max(dol_size, end)

        for i in range(11):
            end = dol_header.data_offset[i] + dol_header.data_length[i]
            dol_size = max(dol_size, end)

        return self.crypto.read_at(dol_offset, dol_size)

    def read_bi2(self) -> bytes:
        bi2_offset = 0x440  # maybe constant though
        bi2_size = 0x2000

        return self.crypto.read_at(bi2_offset, bi2_size)

    def list_files(self, node: Optional[FSTNode] = None, prefix: str = "") -> List[str]:
        paths: list[str] = []
        entries = self.fst.entries if node is None else (
            node.children if isinstance(node, FSTDirectory) else []
        )

        for entry in entries:
            full_path = f"{prefix}{entry.name}"
            if isinstance(entry, FSTDirectory):
                paths.extend(self.list_files(entry, full_path + "/"))
            else:
                paths.append(full_path)

        return paths