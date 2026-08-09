"""
Building a partition from a directory tree on disk
"""
import os
from typing import List

from wiithon.disc.structs.certificate import Certificate
from wiithon.disc.structs.disc_header import DiscHeader
from wiithon.disc.structs.tmd import TMD
from wiithon.disc.structs.ticket import Ticket
from wiithon.disc.enums import WiiPartType

from wiithon.builder.source import PartitionSource
from wiithon.fst.tree import FST
from wiithon.fst.node import FSTFile, FSTDirectory

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
    if not os.path.isdir(path):
        return
    entries = sorted(os.scandir(path), key=lambda e: e.name.lower())
    for entry in entries:
        filename = entry.name
        if entry.is_dir():
            fst_dir = FSTDirectory(filename)
            current_entries.append(fst_dir)
            _build_from_directory_tree_recursive(entry.path, fst_dir.children)
        else:
            fst_file = FSTFile(filename, 0, os.stat(entry.path).st_size)
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
        """
        Read every system file of the extracted partition and build its file system table

        Encryption and hash verification are force-enabled in the internal disc header, whatever the extracted
        header said, since the builder always writes an encrypted and hashed partition

        Args:
            path: Root of the extracted partition, the folder holding ``sys`` and ``files``
            partition_type: Type to record in the partition table

        Raises:
            FileNotFoundError: If any of the expected system files is missing
            InvalidFormatError: If one of them cannot be parsed

        Note:
            Exactly three certificates are read from ``cert.bin``, which is what retail discs carry
        """
        sys_folder = os.path.join(path, "sys")

        #: Folder holding the game files, mirrored by the file system table
        self.files_dir: str = os.path.join(path, "files")
        
        with open(os.path.join(sys_folder, "boot.bin"), 'rb') as f:
            #: Internal disc header, with encryption and hash verification forced on
            self.encrypted_header: DiscHeader = DiscHeader.read(f)
        self.encrypted_header.disable_disc_encryption = 0
        self.encrypted_header.disable_hash_verification = 0

        with open(os.path.join(sys_folder, "bi2.bin"), 'rb') as f:
            #: Disc configuration block read from ``sys/bi2.bin``
            self.bi2: bytes = f.read()

        with open(os.path.join(sys_folder, "apploader.img"), 'rb') as f:
            #: Apploader read from ``sys/apploader.img``
            self.apploader: bytes = f.read()

        with open(os.path.join(sys_folder, "main.dol"), 'rb') as f:
            #: Executable read from ``sys/main.dol``, kept as raw bytes
            self.dol: bytes = f.read()

        with open(os.path.join(path, "tmd.bin"), 'rb') as f:
            #: Title metadata read from ``tmd.bin``
            self.tmd: TMD = TMD.read(f)

        with open(os.path.join(path, "cert.bin"), 'rb') as f:
            #: Certificate chain read from ``cert.bin``
            self.certificates: List[Certificate] = []
            for _ in range(3):
                self.certificates.append(Certificate.read(f))

        with open(os.path.join(path, "ticket.bin"), 'rb') as f:
            #: Ticket read from ``ticket.bin``
            self.ticket: Ticket = Ticket.read(f)

        #: File system table mirroring ``files``
        self.fst: FST = build_from_directory_tree(self.files_dir)

        #: Type recorded in the partition table
        self.partition_type: int = partition_type

    def get_partition_type(self) -> WiiPartType:
        return self.partition_type

    def get_tmd(self) -> TMD:
        return self.tmd

    def get_certificates(self) -> List[Certificate]:
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

    def get_file_data(self, path: List[str]) -> bytes:
        """
        Read one file from the ``files`` directory

        Args:
            path: Path split into components, from the root of the partition

        Returns:
            The file content

        Raises:
            FileNotFoundError: If the file disappeared between the construction of the tree and this call
        """
        rel_path = os.path.join(*path)
        file_path = os.path.join(self.files_dir, rel_path) # pycharm yells at me because arguments are not correct lmao
        with open(file_path, 'rb') as f:
            return f.read()
