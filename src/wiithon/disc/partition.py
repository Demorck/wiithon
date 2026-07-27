from collections.abc import Callable
from io import BytesIO
from typing import List, Optional

from wiithon.crypto.part_reader import CryptPartReader
from wiithon.disc.layout import APPLOADER_OFFSET, APPLOADER_HEADER_SIZE, BI2_OFFSET, BI2_SIZE
from wiithon.fst.tree import FST
from wiithon.fst.node import FSTNode, FSTDirectory, FSTFile
from wiithon.disc.structs.apploader_header import ApploaderHeader
from wiithon.disc.structs.certificate import Certificate
from wiithon.disc.structs.disc_header import DiscHeader
from wiithon.disc.structs.tmd import TMD
from wiithon.disc.structs.partition_header import WiiPartitionHeader
from wiithon.formats.dol import DOL, DOL_HEADER_SIZE, DOL_TEXT_SECTIONS, DOL_DATA_SECTIONS


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
        apploader_offset = APPLOADER_OFFSET
        header_data = self.crypto.read_at(apploader_offset, APPLOADER_HEADER_SIZE)
        apploader_header = ApploaderHeader.read(BytesIO(header_data))
        total_size = APPLOADER_HEADER_SIZE + apploader_header.size1 + apploader_header.size2

        return self.crypto.read_at(apploader_offset, total_size)

    def read_dol(self) -> DOL:
        dol_offset = self.internal_header.DOL_offset
        header_data = self.crypto.read_at(dol_offset, DOL_HEADER_SIZE)
        dol_header = DOL.read(BytesIO(header_data))

        dol_size = DOL_HEADER_SIZE
        for i in range(DOL_TEXT_SECTIONS):
            end = dol_header.header.text_offset[i] + dol_header.header.text_length[i]
            dol_size = max(dol_size, end)

        for i in range(DOL_DATA_SECTIONS):
            end = dol_header.header.data_offset[i] + dol_header.header.data_length[i]
            dol_size = max(dol_size, end)

        dol_data = self.crypto.read_at(dol_offset, dol_size)
        return DOL.read(BytesIO(dol_data))

    def read_bi2(self) -> bytes:
        bi2_offset = BI2_OFFSET
        bi2_size = BI2_SIZE

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

    def callback_all_files(self, callback: Callable[[FSTNode], None], node: Optional[FSTNode] = None) -> None:
        entries = self.fst.entries if node is None else (
            node.children if isinstance(node, FSTDirectory) else []
        )

        for entry in entries:
            if isinstance(entry, FSTDirectory):
                self.callback_all_files(callback, entry)
            else:
                callback(entry)