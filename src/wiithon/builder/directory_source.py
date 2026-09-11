"""
Building a partition from a directory tree on disk
"""
from pathlib import Path

from wiithon.builder.source import PartitionSource
from wiithon.disc.enums import WiiPartType
from wiithon.disc.structs.certificate import Certificate
from wiithon.disc.structs.disc_header import DiscHeader
from wiithon.disc.structs.ticket import Ticket
from wiithon.disc.structs.tmd import TMD
from wiithon.fst.node import FSTDirectory, FSTFile
from wiithon.fst.tree import FST


def build_from_directory_tree(files_dir: str) -> FST:
    """
    Build a file system table mirroring a directory

    Directories are walked recursively. Entries are sorted by name, case insensitively, so the resulting tree is
    stable across platforms and filesystems

    File nodes carry the size read from disk and an offset of zero, since the builder assigns real offsets when it
    writes the data

    Args:
        files_dir: Directory to mirror, typically the ``files`` folder of an extracted partition

    Returns:
        The tree. An empty tree is returned if the path is not a directory
    """
    fst = FST()
    _build_from_directory_tree_recursive(files_dir, fst.entries)
    return fst

def _build_from_directory_tree_recursive(path: str, current_entries: list) -> None:
    # Ordered
    target_path = Path(path)
    if not target_path.is_dir():
        return

    entries = sorted(target_path.iterdir(), key=lambda e: e.name.lower())
    for entry in entries:
        if entry.is_dir():
            fst_dir = FSTDirectory(entry.name)
            current_entries.append(fst_dir)
            _build_from_directory_tree_recursive(str(entry), fst_dir.children)
        else:
            fst_file = FSTFile(entry.name, 0, entry.stat().st_size)
            current_entries.append(fst_file)

class DirectoryPartitionSource(PartitionSource):
    """
    Feeds the builder from a partition extracted to disk

    The layout expected is the one produced by extraction tools such as wit::

        <path>/
            ticket.bin
            tmd.bin
            cert.bin
            sys/
                boot.bin
                bi2.bin
                apploader.img
                main.dol
            files/
                ...

    Everything except the file contents is read in the constructor. File data is read from disk on demand as the
    builder asks for it

    Note:
        ``h3.bin`` and ``disc/`` are ignored if present. The H3 table is recomputed while encrypting, and the
        region belongs to the disc rather than to a partition, so you pass it to
        :class:`~wiithon.builder.disc_builder.WiiDiscBuilder` yourself

    Example:
        >>> source = DirectoryPartitionSource("extracted/DATA", WiiPartType.DATA)

    See Also:
        :class:`~wiithon.builder.copy_source.CopyPartitionSource` to build from an existing ISO instead
    """
    def __init__(self, path: str, partition_type: WiiPartType) -> None:
        base_path = Path(path)

        sys_folder = base_path / "sys"
        #: Folder holding the game files, mirrored by the file system table
        self.files_dir = str(base_path / "files")

        with (sys_folder / 'boot.bin').open('rb') as f:
            #: Internal disc header, with encryption and hash verification forced on
            self.encrypted_header = DiscHeader.read(f)
        self.encrypted_header.disable_disc_encryption = 0
        self.encrypted_header.disable_hash_verification = 0

        #: Disc configuration block read from ``sys/bi2.bin``
        self.bi2 = (sys_folder / "bi2.bin").read_bytes()

        #: Apploader read from ``sys/apploader.img``
        self.apploader = (sys_folder / "apploader.img").read_bytes()

        #: Executable read from ``sys/main.dol``, kept as raw bytes
        self.dol = (sys_folder / "main.dol").read_bytes()

        with (base_path / "tmd.bin").open('rb') as f:
            #: Title metadata read from ``tmd.bin``
            self.tmd = TMD.read(f)

        with (base_path / "cert.bin").open('rb') as f:
            #: Certificate chain read from ``cert.bin``
            self.certificates = []
            for _ in range(3):
                self.certificates.append(Certificate.read(f))

        with (base_path / "ticket.bin").open('rb') as f:
            #: Ticket read from ``ticket.bin``
            self.ticket = Ticket.read(f)

        #: File system table mirroring ``files``
        self.fst: FST = build_from_directory_tree(self.files_dir)

        #: Type recorded in the partition table
        self.partition_type: int = partition_type

    def get_partition_type(self) -> WiiPartType:
        return self.partition_type

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

    def get_ticket(self) -> Ticket:
        return self.ticket

    def get_dol(self) -> bytes:
        return self.dol

    def get_fst(self) -> FST:
        return self.fst

    def get_file_data(self, path: list[str]) -> bytes:
        """
        Read one file from the ``files`` directory

        Args:
            path: Path split into components, from the root of the partition

        Returns:
            The file content

        Raises:
            FileNotFoundError: If the file disappeared between the construction of the tree and this call
        """
        file_path = Path(self.files_dir).joinpath(*path)
        return file_path.read_bytes()
