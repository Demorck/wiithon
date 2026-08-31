import hashlib
from io import BytesIO
from typing import BinaryIO

from wiithon.binary.align import align
from wiithon.binary.reader import BinaryReader
from wiithon.crypto.layout import GROUP_SIZE
from wiithon.exceptions import CorruptedDataError
from wiithon.rvz.enums import WiaCompression
from wiithon.rvz.layout import DISC_OFFSET, DISC_SIZE, PARTITION_SIZE
from wiithon.rvz.structs.disc import WiaDisc
from wiithon.rvz.structs.exception_list import WiaExceptionList
from wiithon.rvz.structs.file_header import WiaHeader
from wiithon.rvz.structs.group import RvzGroup, WiaGroup
from wiithon.rvz.structs.partition import WiaPartition
from wiithon.rvz.structs.raw_data import WiaRawData


class WiaReader:
    """
    Reads the structure of a WIA or RVZ image

    Mimic the WiiIsoReader
    """

    def __init__(self, path: str) -> None:
        self.path = path
        self.file: BinaryIO = open(path, "rb") # noqa: SIM115

        try:
            self.header: WiaHeader = WiaHeader.read(self.file)
            self.disc: WiaDisc = WiaDisc.read(self._read_verified(
                DISC_OFFSET, self.header.disc_size, self.header.disc_hash,
                DISC_SIZE, "Disc structure",
            ))
            self.partitions: list[WiaPartition] = self._read_partitions()

            #: Lazy raw data
            self._raw_data: list[WiaRawData] | None = None

            #: Lazy groups
            self._groups: list[WiaGroup] | None = None

        except BaseException:
            self.file.close()
            raise

    def __enter__(self) -> "WiaReader":
        return self

    def __exit__(self, *args) -> None:
        self.close()


    @property
    def group_class(self) -> type[WiaGroup]:
        """
        The group structure this image uses

        Returns:
            ``RVZGroup`` for an RVZ image. ``WiaGroup`` for a WIA image.
        """
        return RvzGroup if self.header.is_rvz else WiaGroup

    @property
    def raw_data(self) -> list[WiaRawData]:
        """
        Descriptors living outside a partition

        Returns:
            One descriptor per raw data area

        Raises:
            NotImplementedError: If the image is compressed
        """
        if self._raw_data is None:
            stream = self._read_stored(self.disc.raw_data_offset, self.disc.raw_data_size)
            self._raw_data = [WiaRawData.read(stream) for _ in range(self.disc.raw_data_count)]

        return self._raw_data

    @property
    def groups(self) -> list[WiaGroup]:
        """
        Descriptors pointing at every chunk of stored data.

        Returns:
            One descriptor per group

        Raises:
            NotImplementedError: If the image is compressed by a compression not currently implemented
            CorruptedDataError: If the array does not have the right size
        """
        if self._groups is None:
            expected = self.disc.group_count * self.group_class.STRUCT_SIZE
            if self.disc.compression == WiaCompression.NONE and self.disc.group_size != expected:
                raise CorruptedDataError(
                    f"Group array is {self.disc.group_size} bytes expected {expected}"
                )

            stream = self._read_stored(self.disc.group_offset, self.disc.group_size)
            self._groups = [self.group_class.read(stream) for _ in range(self.disc.group_count)]

        return self._groups

    def read_group(self, index: int) -> bytes:
        """
        Read the stored bytes of one group any exception list included

        Args:
            index: Index into :attr:`groups`

        Returns:
            The stored bytes that is empty for a group holding only zeros

        Raises:
            NotImplementedError: If the image is compressed by a compression not currently implemented
        """
        group = self.groups[index]
        if group.is_zero:
            return b''

        if group.is_packed:
            raise NotImplementedError("Decoding the RVZ packing is not supported yet")

        self.file.seek(group.offset)
        return BinaryReader(self.file).raw(group.size)

    def read_partition_group(self, index: int) -> tuple[list[WiaExceptionList], bytes]:
        """
        Read one group of partition data. Splitted into Exception list and the payload

        Args:
            index: Index into :attr:`groups`

        Returns:
            One exception list per hash group, and the decrypted data without its hashes

        Raises:
            NotImplementedError: If the image is compressed by a compression not currently implemented
        """
        count = max(1, self.disc.chunk_size // GROUP_SIZE)
        data = self.read_group(index)
        if not data:
            return [WiaExceptionList() for _ in range(count)], b''

        stream = BytesIO(data)
        exceptions = [WiaExceptionList.read(stream) for _ in range(count)]

        if self.disc.compression in (
                WiaCompression.NONE,
                WiaCompression.PURGE
        ):
            stream.seek(align(stream.tell(), 4))

        return exceptions, stream.read()

    def close(self) -> None:
        self.file.close()

    def _read_verified(self, offset: int, size: int, expected_hash: bytes,
                       padded_to: int, what: str) -> BytesIO:
        """
        Read a structure block, check its hash and pad it so a shorter block written
        by an older writer still parses

        Args:
            offset: Where the block starts in the file
            size: Number of bytes the hash covers
            expected_hash: SHA1 the block must match
            padded_to: Size this version expects the structure to have
            what: Name used in the error message

        Returns:
            A stream over the padded block

        Raises:
            CorruptedDataError: If the hash does not match
        """
        self.file.seek(offset)
        raw = BinaryReader(self.file).raw(size)
        if hashlib.sha1(raw).digest() != expected_hash:
            raise CorruptedDataError(f"{what} in WIA/RVZ has a hash mismatch")

        return BytesIO(raw.ljust(padded_to, b'\x00'))

    def _read_partitions(self) -> list[WiaPartition]:
        """
        Read the partition descriptors, which are never compressed.

        Returns:
            One descriptor per partition of the disc
        """
        stream = self._read_verified(
            self.disc.partition_offset,
            self.disc.partition_count * self.disc.partition_struct_size,
            self.disc.partition_hash,
            self.disc.partition_count * PARTITION_SIZE,
            "Partition array",
        )
        return [WiaPartition.read(stream) for _ in range(self.disc.partition_count)]

    def _read_stored(self, offset: int, size: int) -> BytesIO:
        """
        Read a block the image stores compressed

        Args:
            offset: Where the block starts in the file
            size: How many bytes it takes on file

        Returns:
            A stream over the block

        Raises:
            NotImplementedError: If the image is compressed
        """
        if self.disc.compression != WiaCompression.NONE:
            raise NotImplementedError(
                f"Reading a {self.disc.compression.name} image is not supported yet"
            )

        self.file.seek(offset)
        return BytesIO(BinaryReader(self.file).raw(size))
