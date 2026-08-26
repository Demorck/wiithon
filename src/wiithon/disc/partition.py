"""
Access to the contents of a decrypted disc partition

Instances of :class:`WiiPartitionInfo` are produced by
:meth:`wiithon.disc.reader.WiiIsoReader.open_partition`. They are not meant to be
built directly
"""

from collections.abc import Callable
from io import BytesIO

from wiithon.crypto.part_reader import CryptPartReader
from wiithon.disc.layout import APPLOADER_HEADER_SIZE, APPLOADER_OFFSET, BI2_OFFSET, BI2_SIZE
from wiithon.disc.structs.apploader_header import ApploaderHeader
from wiithon.disc.structs.certificate import Certificate
from wiithon.disc.structs.disc_header import DiscHeader
from wiithon.disc.structs.partition_header import WiiPartitionHeader
from wiithon.disc.structs.tmd import TMD
from wiithon.exceptions import FstFileNotFoundError, FstIsADirectoryError
from wiithon.formats.dol import DOL, DOL_DATA_SECTIONS, DOL_HEADER_SIZE, DOL_TEXT_SECTIONS
from wiithon.formats.dol_header import DOLHeader
from wiithon.fst.node import FSTDirectory, FSTFile, FSTNode
from wiithon.fst.tree import FST


class WiiPartitionInfo:
    """
    A decrypted partition and everything it contains

    All reads go through a :class:`~wiithon.crypto.part_reader.CryptPartReader`,
    which decrypts blocks on demand. Nothing is held in memory beyond the file
    system table, so reading a large file costs a disc read, not a full partition
    decryption
    """
    def __init__(self,  header: WiiPartitionHeader, tmd: TMD,
                        certificates: list[Certificate], internal_header: DiscHeader,
                        fst: FST, crypto: CryptPartReader,
                        partition_offset: int) -> None:
        #: Partition header, holding the ticket and the offsets to the TMD, certificates, H3 table and data
        self.header: WiiPartitionHeader = header

        #: Title metadata, describing the contents and their SHA-1 hashes
        self.tmd: TMD = tmd

        #: The partition certificate chain
        self.certificates: list[Certificate] = certificates

        #: Disc header found at offset ``0x000`` of the decrypted data, also known as ``boot.bin``
        #: This is where the DOL and FST offsets live
        self.internal_header: DiscHeader = internal_header

        #: Parsed file system table
        self.fst: FST = fst

        #: Decrypting reader used for every access to partition data
        self.crypto: CryptPartReader = crypto

        #: Absolute offset of the partition within the ISO
        self.partition_offset: int = partition_offset

    def read_file(self, path: str) -> bytes:
        """
        Read a file from the partition

        Args:
            path: Path inside the partition, using ``/`` as separator, for example
		``"StageData/HeavensDoorGalaxy.arc"``

        Returns:
            The decrypted file contents

        Raises:
            FstFileNotFoundError: If no node matches ``path``
            FstIsADirectoryError: If ``path`` resolves to a directory
        """
        node = self.fst.find_node(path)

        if node is None:
            raise FstFileNotFoundError(f"File not found: {path}")

        if not isinstance(node, FSTFile):
            raise FstIsADirectoryError(f"Path is a directory: {path}")

        return self.crypto.read_at(node.offset, node.length)


    def read_apploader(self) -> bytes:
        """
		Read the apploader, the code that boots the game

		The apploader header declares two payload sizes. Both are read along with
		the header itself

		Returns:
            The complete apploader, header included
		"""

        apploader_offset = APPLOADER_OFFSET
        header_data = self.crypto.read_at(apploader_offset, APPLOADER_HEADER_SIZE)
        apploader_header = ApploaderHeader.read(BytesIO(header_data))
        total_size = APPLOADER_HEADER_SIZE + apploader_header.size1 + apploader_header.size2

        return self.crypto.read_at(apploader_offset, total_size)

    def read_dol(self) -> DOL:
        """
		Read and parse the main executable

		The DOL has no explicit size on disc, so it is computed as the furthest end
		of any text or data section declared in its header

		Returns:
            The parsed :class:`~wiithon.formats.dol.DOL`
		"""
        dol_offset = self.internal_header.DOL_offset
        header_data = self.crypto.read_at(dol_offset, DOL_HEADER_SIZE)
        header = DOLHeader.read(BytesIO(header_data))

        dol_size = DOL_HEADER_SIZE
        for i in range(DOL_TEXT_SECTIONS):
            dol_size = max(dol_size, header.text_offset[i] + header.text_length[i])

        for i in range(DOL_DATA_SECTIONS):
            dol_size = max(dol_size, header.data_offset[i] + header.data_length[i])

        dol_data = self.crypto.read_at(dol_offset, dol_size)
        return DOL.read(BytesIO(dol_data))

    def read_bi2(self) -> bytes:
        """
		Read ``bi2.bin``, the disc configuration block that follows the header

		Returns:
            The raw block, read at its fixed offset and size
		"""
        bi2_offset = BI2_OFFSET
        bi2_size = BI2_SIZE

        return self.crypto.read_at(bi2_offset, bi2_size)

    def list_files(self, node: FSTNode | None = None, prefix: str = "") -> list[str]:
        """
        List every file in the partition, recursively

        Directories are traversed but not listed. Only files appear in the result

        Args:
            node: Directory to start from. Defaults to the root of the FST
            prefix: Path prefix prepended to each result

        Returns:
            Full paths, using ``/`` as separator

        Note:
            ``node`` and ``prefix`` drive the recursion and are not meant to be
            passed by callers. On a large disc the whole list is built in memory,
            so prefer :meth:`callback_all_files` when you only need to walk it
        """
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

    def callback_all_files(self, callback: Callable[[FSTNode], None], node: FSTNode | None = None) -> None:
        """
        Walk every file in the partition and invoke a callback on each

        Directories are traversed but never passed to the callback

        Args:
            callback: Called once per file, with the FST node as its only argument
            node: Directory to start from. Defaults to the root of the FST

        Note:
            The callback receives the node, not the full path. If you need paths,
            use :meth:`list_files`
        """
        entries = self.fst.entries if node is None else (
            node.children if isinstance(node, FSTDirectory) else []
        )

        for entry in entries:
            if isinstance(entry, FSTDirectory):
                self.callback_all_files(callback, entry)
            else:
                callback(entry)