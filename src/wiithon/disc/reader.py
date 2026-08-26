"""
Read-only access to a Wii disc image

This module exposes :class:`WiiIsoReader`, the entry point for inspecting an ISO
without modifying it. To modify one, see :mod:`wiithon.disc.patcher`
"""

from io import BytesIO
from pathlib import Path
from typing import BinaryIO

from wiithon.binary.reader import BinaryReader
from wiithon.crypto.part_reader import CryptPartReader
from wiithon.disc.enums import WiiPartType
from wiithon.disc.layout import (
    DISC_HEADER_SIZE,
    MAGIC_WORD_OFFSET,
    REGION_OFFSET,
    REGION_SIZE,
    WII_MAGIC_WORD,
)
from wiithon.disc.partition import WiiPartitionInfo
from wiithon.disc.structs.certificate import Certificate
from wiithon.disc.structs.disc_header import DiscHeader
from wiithon.disc.structs.partition_entry import WiiPartitionEntry, read_parts
from wiithon.disc.structs.partition_header import WiiPartitionHeader
from wiithon.disc.structs.tmd import TMD
from wiithon.exceptions import InvalidDiscError
from wiithon.fst.tree import FST


class WiiIsoReader:
    """
    Read-only view of a Wii disc image

    Opening a reader parses the unencrypted disc header and the partition table
    immediately, then validates the Wii magic word. Partitions themselves are read
    lazily, only when :meth:`open_partition` is called

    The reader holds an open file handle for its whole lifetime. Use it as a
    context manager so the handle is released even when an error occurs

    Example:
        >>> with WiiIsoReader("game.iso") as reader:
        ...     partition = reader.open_partition(reader.get_data_partition())
        ...     data = partition.read_file("opening.bnr")
    """

    def __init__(self, path: str) -> None:
        """
        Open an ISO and parse its header and partition table

        Args:
            path: Path to the disc image

        Raises:
            InvalidDiscError: If the Wii magic word is missing or wrong, which
                usually means the file is not a Wii disc image
            OSError: If the file cannot be opened

        Note:
            The file handle is closed automatically if parsing fails, so a failed
            construction never leaks a descriptor
        """
        #: Path the reader was opened on.
        self._path = Path(path)

        #: Underlying binary file handle.
        self.file: BinaryIO = self._path.open("rb") # noqa: SIM115
        try:
            #: Unencrypted disc header, read from offset ``0x000``.
            self.disc_header: DiscHeader = DiscHeader.read(self.file)

            #: Every entry of the partition table, in disc order
            self.partitions: list[WiiPartitionEntry] = read_parts(self.file)

            #: Raw region bytes
            self.region: bytes = self.read_region()

            #: Wii magic word, validated at construction
            self.magic_word: int = self.read_magic_word()
            if self.magic_word != WII_MAGIC_WORD:
                raise InvalidDiscError(f"Wii magic word is not {WII_MAGIC_WORD:#X}, got {self.magic_word:#X}")
        except BaseException:
            self.file.close()
            raise

    def get_data_partition(self) -> WiiPartitionEntry | None:
        """
        Return the DATA partition entry, which holds the game itself

        Returns:
            The first DATA entry found, or ``None`` if the disc has none
        """
        return next((p for p in self.partitions if p.part_type == WiiPartType.DATA), None)

    def get_update_partition(self) -> WiiPartitionEntry | None:
        """
        Return the UPDATE partition entry, which holds a system update

        Returns:
            The first UPDATE entry found, or ``None``. An update partition is optional and many discs do not carry one
        """
        return next((p for p in self.partitions if p.part_type == WiiPartType.UPDATE), None)

    def get_partitions(self) -> list[WiiPartitionEntry]:
        """
        Return every partition entry listed in the partition table

        Returns:
            The entries in disc order, including types Wiithon cannot open yet such as CHANNEL
        """
        return self.partitions

    def read_region(self) -> bytes:
        """
        Read the raw region bytes from the disc

        Returns:
            The region block, read at its fixed offset

        Note:
            This seeks the underlying file handle. The value is already cached in
            :attr:`region` at construction, so you rarely need to call this
        """
        self.file.seek(REGION_OFFSET)
        return self.file.read(REGION_SIZE)


    def read_magic_word(self) -> int:
        """
        Read the Wii magic word from its fixed offset

        Returns:
            The 32-bit word stored at offset ``0x18``. A valid Wii disc yields ``0x5D1C9EA3``

        Note:
            A Wii disc carries a second marker ``0xC3F81A8E`` at offset ``0x4FFFC``, which describes the
            partition layout rather than the disc itself. It is exposed as ``SYSTEM_MAGIC_WORD``
        """
        reader = BinaryReader(self.file)
        reader.seek(MAGIC_WORD_OFFSET)
        return reader.u32()


    def open_partition(self, entry: WiiPartitionEntry) -> WiiPartitionInfo:
        """
        Decrypt a partition and load its file system table

        This reads the partition header, the TMD and the certificate chain, then
        sets up AES decryption using the title key from the ticket. It finally
        reads the internal disc header and the FST from the decrypted data

        Args:
            entry: Partition table entry, obtained from :meth:`get_data_partition`,
                :meth:`get_update_partition` or :meth:`get_partitions`

        Returns:
            A :class:`~wiithon.disc.partition.WiiPartitionInfo` giving access to
            the files inside the partition

        Warning:
            CHANNEL partitions are not supported yet

        Note:
            The certificate chain is assumed to hold exactly three certificates,
            which covers every retail disc seen so far
        """
        offset = entry.offset

        # Reading partition header
        self.file.seek(offset)
        header = WiiPartitionHeader.read(self.file)

        # Reading TMD
        self.file.seek(offset + header.tmd_offset)
        tmd = TMD.read(self.file)

        # Reading certificates
        self.file.seek(offset + header.certificate_chain_offset)
        certificates: list[Certificate] = [Certificate.read(self.file) for _ in range(3)]

        # Crypto header for decrypted data
        data_offset = offset + header.data_offset
        title_key = header.ticket.title_key
        crypto = CryptPartReader(self.file, data_offset, title_key)

        # Disc Header
        boot_data = crypto.read_at(0, DISC_HEADER_SIZE)
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
        """
        Close the underlying file handle

        Called automatically when leaving a ``with`` block
        """
        self.file.close()

    def __enter__(self) -> "WiiIsoReader":
        return self

    def __exit__(self, *args: int) -> None:
        self.close()