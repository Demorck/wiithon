import copy
import os

from typing import Callable, List, Optional, Any

from wiithon.structs.Certificate import Certificate
from wiithon.structs.DiscHeader import DiscHeader
from wiithon.structs.TMD import TMD
from wiithon.structs.Ticket import Ticket
from wiithon.structs.WiiPartitionEntry import WiiPartitionEntry
from wiithon.helpers.Enums import WiiPartType
from wiithon.file_helper.dol import DOL

from wiithon.WiiIsoReader import WiiIsoReader
from wiithon.builder.WiiPartitionInterface import WiiPartitionInterface
from wiithon.file_system_table.FST import FST


class CopyBuilder(WiiPartitionInterface):
    """
    Builder class to copy and optionally modify a Wii partition.

    This class reads partition data from a source ISO, allows on-the-fly
    modifications to the File System Table (FST) and the main executable (DOL),
    and supports injecting custom file overrides.
    """

    partition_info: Any
    """Internal partition handler returned by the WiiIsoReader."""

    partition_type: int
    """The numerical type of the partition."""

    bi2: bytes
    """Raw data of the BI2 (Disk Header Information) section."""

    apploader: bytes
    """Raw data of the partition's apploader."""

    dol: DOL
    """The main executable (DOL) of the partition."""

    tmd: TMD
    """Title Metadata (TMD) for the partition."""

    certificates: List[Certificate]
    """List of certificates associated with the partition."""

    fst: FST
    """The File System Table (FST) representing the partition's directory structure."""

    encrypted_header: DiscHeader
    """The encrypted internal header of the partition."""

    ticket: Ticket
    """The ticket containing partition decryption keys."""

    _file_overrides: dict[str, bytes]
    """Internal dictionary storing specific files to replace during the build process."""

    def __init__(self, reader: WiiIsoReader, partition: WiiPartitionEntry,
                 fst_modifier: Optional[Callable[[FST], None]] = None,
                 dol_modifier: Optional[Callable[[DOL], None]] = None,
                 file_overrides: dict[str, bytes] | None = None) -> None:
        copy_partition = copy.copy(partition)
        self.partition_info = reader.open_partition(copy_partition)
        self.partition_type = partition.part_type
        self.bi2 = self.partition_info.read_bi2()
        self.apploader = self.partition_info.read_apploader()
        self.dol = self.partition_info.read_dol()
        self.tmd = self.partition_info.tmd
        self.certificates = self.partition_info.certificates
        self.fst = copy.copy(self.partition_info.fst)
        self.encrypted_header = self.partition_info.internal_header
        self.ticket = self.partition_info.header.ticket

        if fst_modifier is not None:
            fst_modifier(self.fst)

        if dol_modifier is not None:
            dol_modifier(self.dol)

        self._file_overrides: dict[str, bytes] = file_overrides or {}

    def get_partition_type(self) -> WiiPartType:
        """
        Retrieves the formatted partition type.

        Returns:
            The parsed partition type as an enum.
        """
        return WiiPartType(self.partition_type)

    def get_ticket(self) -> Ticket:
        """
        Retrieves the ticket associated with this partition.

        Returns:
            The partition's ticket object.
        """
        return self.ticket

    def get_tmd(self) -> TMD:
        """
        Retrieves the Title Metadata (TMD) for this partition.

        Returns:
            The partition's TMD object.
        """
        return self.tmd

    def get_certificates(self) -> List[Certificate]:
        """
        Retrieves the chain of certificates.

        Returns:
            A list containing the certificates of the partition.
        """
        return self.certificates

    def get_encrypted_header(self) -> DiscHeader:
        """
        Retrieves the encrypted internal header.

        Returns:
            The partition's DiscHeader object.
        """
        return self.encrypted_header

    def get_bi2(self) -> bytes:
        """
        Retrieves the BI2 disk information data.

        Returns:
            The raw BI2 bytes.
        """
        return self.bi2

    def get_apploader(self) -> bytes:
        """
        Retrieves the apploader binary.

        Returns:
            The raw apploader bytes.
        """
        return self.apploader

    def get_dol(self) -> bytes:
        """
        Retrieves the main executable of the partition.

        Returns:
            The packed bytes representing the potentially modified DOL file.
        """
        return self.dol.to_bytes()

    def get_fst(self) -> FST:
        """
        Retrieves the File System Table.

        Returns:
            The potentially modified FST object.
        """
        return self.fst

    def get_file_data(self, path: List[str]) -> bytes:
        """
        Retrieves the raw binary data of a file within the partition.

        This method first checks if the requested file exists in the file overrides.
        If not, it attempts to locate and decrypt it from the original partition
        using the File System Table (FST).

        Args:
            path: A list of directory and file names representing the internal path.

        Returns:
            The raw bytes of the requested file.

        Raises:
            FileNotFoundError: If the file cannot be found in the FST or overrides.
        """
        key = "/".join(path)
        if key in self._file_overrides:
            return self._file_overrides[key]

        node = self.fst.find_node(os.path.join(*path) if path else "")
            
        if node and not hasattr(node, "children"): # ie: is a file
            data = self.partition_info.crypto.read_at(node.original_offset, node.length)
            return data

        raise FileNotFoundError(f"File not found in FST: {path}")
