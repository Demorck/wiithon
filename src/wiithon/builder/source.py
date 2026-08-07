"""The contract a partition must fulfil to be written by the builder"""
from abc import ABC, abstractmethod
from typing import List

from wiithon.disc.structs.certificate import Certificate
from wiithon.disc.structs.disc_header import DiscHeader
from wiithon.disc.structs.tmd import TMD
from wiithon.disc.structs.ticket import Ticket
from wiithon.fst.tree import FST


class PartitionSource(ABC):
    """
    Describes where the content of one partition comes from

    :class:`~wiithon.builder.disc_builder.WiiDiscBuilder` never reads a disc or a directory itself. It asks a
    ``PartitionSource`` for each piece it needs, in the order below, and writes what it gets back

    Two implementations ship with the library:

    - :class:`~wiithon.builder.copy_source.CopyPartitionSource` reads from an existing ISO
    - :class:`~wiithon.builder.directory_source.DirectoryPartitionSource` reads from a directory tree

    Implement this class to build a partition from anywhere else

    Note:
        The builder calls the getters in this order: :meth:`get_partition_type`, :meth:`get_ticket`, :meth:`get_tmd`,
        :meth:`get_certificates`, :meth:`get_fst`, :meth:`get_encrypted_header`, :meth:`get_bi2`,
        :meth:`get_apploader`, :meth:`get_dol`, then :meth:`get_file_data` once per file

    See Also:
        :doc:`/user_guide/patching` for the common cases that do not need a custom source
    """
    @abstractmethod
    def get_partition_type(self) -> int:
        """
        Return the type of the partition

        Returns:
            A :class:`~wiithon.disc.enums.WiiPartType` value
        """
    
    @abstractmethod
    def get_tmd(self) -> TMD:
        """
        Return the title metadata

        Returns:
            The TMD. The builder rewrites its H3 hash, its data size and its signature padding before writing it,
            so the content hashes it carries do not need to be correct
        """
    
    @abstractmethod
    def get_certificates(self) -> List[Certificate]:
        """
        Return the certificate chain of the partition

        Returns:
            The certificates, written back to back in the order given. Retail discs carries three
        """
    
    @abstractmethod
    def get_encrypted_header(self) -> DiscHeader:
        """
        Return the disc header stored at offset 0 of the partition data

        This is the internal header, also known as ``boot.bin``, not the unencrypted one at the start of the disc.
        The builder overwrites its DOL and FST offsets once it knows where those landed

        Returns:
            The header to place at the beginning of the partition data
        """
    
    @abstractmethod
    def get_bi2(self) -> bytes:
        """
        Return the BI2

        Returns:
            The raw block, written at its fixed offset
        """
    
    @abstractmethod
    def get_apploader(self) -> bytes:
        """
        Return the apploader, the code that boots the game

        Returns:
            The complete apploader, its own header included
        """
    
    @abstractmethod
    def get_dol(self) -> bytes:
        """
        Return the main executable

        Returns:
            The DOL as raw bytes, not a parsed :class:`~wiithon.formats.dol.DOL`. Serialise it yourself if you
            hold an object
        """
    
    @abstractmethod
    def get_fst(self) -> FST:
        """
        Return the file system table of the partition

        The tree drives everything that follows: the builder walks it to know which files to ask for, and rewrites
        the offset and length of each node once the data is placed

        Returns:
            The tree of directories and files
        """
    
    @abstractmethod
    def get_ticket(self) -> Ticket:
        """
        Return the ticket of the partition

        The builder takes the title key from it to encrypt every block of partition data, so this is the first
        thing it needs

        Returns:
            The ticket, written at offset 0 of the partition
        """
    
    @abstractmethod
    def get_file_data(self, path: List[str]) -> bytes:
        """
        Return the content of one file

        Called once per file found in the FST, in the order the builder writes them

        Args:
            path: Path split into components, from the root of the partition down to the file name, for example
                ``["StageData", "AstroDome", "AstroDome.arc"]`` is "StageData/AstroDome/AstroDome.arc"

        Returns:
            The file content. Its length overrides whatever the FST node declared
        """
