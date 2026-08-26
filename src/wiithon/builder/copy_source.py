"""
Building a partition from one already present in an ISO
"""
import copy
from collections.abc import Callable
from pathlib import Path

from wiithon.builder.source import PartitionSource
from wiithon.disc.partition import WiiPartitionInfo
from wiithon.disc.reader import WiiIsoReader
from wiithon.disc.structs.certificate import Certificate
from wiithon.disc.structs.disc_header import DiscHeader
from wiithon.disc.structs.partition_entry import WiiPartitionEntry
from wiithon.disc.structs.ticket import Ticket
from wiithon.disc.structs.tmd import TMD
from wiithon.exceptions import FstFileNotFoundError
from wiithon.formats.dol import DOL
from wiithon.fst.tree import FST


class CopyPartitionSource(PartitionSource):
    """
    Feeds the builder from a partition of an existing disc

    Everything is read in the constructor, so building an instance opens the partition and pulls its
    system files immediately. The optional callbacks run at that point too, which means the FST and the DOL handed
    to the builder are already modified

    File data is streamed later, on demand, straight from the source ISO. Only the files you override are held in
    memory

    This is what :class:`~wiithon.disc.patcher.WiiIsoPatcher` uses for every partition of the disc it rebuilds

    Example:
        >>> with WiiIsoReader("game.iso") as reader:
        ...     entry = reader.get_data_partition()
        ...     source = CopyPartitionSource(reader, entry, file_overrides={"opening.bnr": new_banner})
    """
    def __init__(self, reader: WiiIsoReader, partition: WiiPartitionEntry,
                 fst_modifier: Callable[[FST], None] | None = None,
                 dol_modifiers: list[Callable[[DOL], None]] | None = None,
                 file_overrides: dict[str, bytes] | None = None) -> None:
        """
        Open the source partition and apply the modifications

        Args:
            reader: Reader holding the source ISO, kept open for the lifetime of this object
            partition: Entry of the partition to copy
            fst_modifier: Called once with the file system table, before the builder walks it. Modify the tree in
                place, the return value is ignored
            dol_modifier: Called once with the parsed executable. Modify it in place
            file_overrides: Replacement content keyed by full path inside the partition, using ``/`` as separator.
                A path listed here is served from memory instead of being read from the source

        Note:
            The reader must stay open until the build is over, since file data is read lazily from it
        """
        copy_partition = copy.copy(partition)
        #: Partition opened from the source ISO, used to read file data on demand
        self.partition_info: WiiPartitionInfo = reader.open_partition(copy_partition)

        #: Type of the partition being copied
        self.partition_type: int = partition.part_type

        #: Disc configuration block read from the source
        self.bi2: bytes = self.partition_info.read_bi2()

        #: Apploader read from the source
        self.apploader: bytes = self.partition_info.read_apploader()

        #: Parsed executable, already patched if a ``dol_modifier`` was given
        self.dol: DOL = self.partition_info.read_dol()

        #: Title metadata of the source partition
        self.tmd: TMD = self.partition_info.tmd

        #: Certificate chain of the source partition
        self.certificates: list[Certificate] = self.partition_info.certificates

        #: File system table, already modified if a ``fst_modifier`` was given
        self.fst: FST = copy.copy(self.partition_info.fst)

        #: Internal disc header of the source partition
        self.encrypted_header: DiscHeader = self.partition_info.internal_header

        #: Ticket of the source partition, holding the title key
        self.ticket: Ticket = self.partition_info.header.ticket

        if fst_modifier is not None:
            fst_modifier(self.fst)

        if dol_modifiers is None:
            dol_modifiers = []

        for modifier in dol_modifiers:
            modifier(self.dol)

        self._file_overrides: dict[str, bytes] = file_overrides or {}

    def get_partition_type(self) -> int:
        return self.partition_type

    def get_ticket(self) -> Ticket:
        return self.ticket

    def get_tmd(self) -> TMD:
        return self.tmd

    def get_certificates(self) -> list[Certificate]:
        return self.certificates

    def get_encrypted_header(self) -> DiscHeader:
        return self.encrypted_header

    def get_bi2(self) -> bytes:
        return self.bi2

    def get_apploader(self) -> bytes:
        return self.apploader

    def get_dol(self) -> bytes:
        """
        Serialise the executable, including any patch applied by ``dol_modifier``

        Returns:
            The DOL as raw bytes
        """
        return self.dol.to_bytes()

    def get_fst(self) -> FST:
        return self.fst

    def get_file_data(self, path: list[str]) -> bytes:
        """
        Return the content of one file, from the overrides or from the source disc

        Paths present in ``file_overrides`` are served from memory. Everything else is read from the source ISO at
        the offset the node had **before** the builder started moving files around

        Args:
            path: Path split into components, from the root of the partition

        Returns:
            The file content

        Raises:
            FstFileNotFoundError: If the path matches no file, which also covers the case of a path resolving to a
                directory
        """
        key = "/".join(path)
        if key in self._file_overrides:
            return self._file_overrides[key]

        node = self.fst.find_node(str(Path(*path)) if path else "")

        if node and not hasattr(node, "children"):  # ie: is a file
            data = self.partition_info.crypto.read_at(node.original_offset, node.length)
            return data

        raise FstFileNotFoundError(f"File not found in FST: {path}")
