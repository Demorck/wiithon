from WiiPartitionInfo import WiiPartitionInfo
from crypto.CryptPartWriter import CryptPartWriter
from file_system_table.FSTToBytes import FSTToBytes
from structs.Certificate import Certificate
from structs.DiscHeader import DiscHeader
from structs.TMD import TMD
from structs.WiiPartitionEntry import WiiPartitionEntry
from structs.WiiPartitionHeader import WiiPartitionHeader


class CopyBuilder:
    def __init__(
        self,
        entry: WiiPartitionEntry,
        partition_info: WiiPartitionInfo,
        fst_modifier=None,
    ) -> None:
        self._part_type = entry.part_type
        self._info      = partition_info

        if fst_modifier is not None:
            fst_modifier(partition_info.fst)

        self._fst_to_bytes = FSTToBytes(partition_info.fst.entries)

        # Sauvegarde des offsets SOURCE avant que assign_file_offsets les écrase
        self._source_files: list[tuple[int, int]] = []
        self._fst_to_bytes.callback_all_files(
            lambda path, node: self._source_files.append((node.offset, node.length))
        )

    def get_part_type(self)         -> int:                 return self._part_type
    def get_header(self)            -> WiiPartitionHeader:  return self._info.header
    def get_tmd(self)               -> TMD:                 return self._info.tmd
    def get_certificates(self)      -> list[Certificate]:   return self._info.certificates
    def get_internal_header(self)   -> DiscHeader:          return self._info.internal_header
    def get_bi2(self)               -> bytes:               return self._info.read_bi2()
    def get_apploader(self)         -> bytes:               return self._info.read_apploader()
    def get_dol(self)               -> bytes:               return self._info.read_dol()
    def get_fst_to_bytes(self)      -> FSTToBytes:          return self._fst_to_bytes

    def assign_file_offsets(self, start: int) -> None:
        current = start
        def on_file(path, node):
            nonlocal current
            node.offset  = current
            current     += node.length   # length inchangé depuis source
            current = (current + 3) & ~3
        self._fst_to_bytes.callback_all_files(on_file)

    def write_file_data(self, writer: CryptPartWriter, progress_cb=None) -> int:
        total = len(self._source_files)
        for i, (src_offset, src_length) in enumerate(self._source_files):
            if src_length > 0:
                data = self._info.crypto.read_at(src_offset, src_length)
                writer.write(data)
            if progress_cb and total > 0:
                progress_cb((i + 1) * 100 // total)
        return total
