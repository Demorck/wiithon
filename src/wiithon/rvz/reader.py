import hashlib
from io import BytesIO
from typing import BinaryIO

from wiithon.binary.reader import BinaryReader
from wiithon.exceptions import CorruptedDataError
from wiithon.rvz.layout import DISC_OFFSET, DISC_SIZE, PARTITION_SIZE
from wiithon.rvz.structs.disc import WiaDisc
from wiithon.rvz.structs.file_header import WiaHeader
from wiithon.rvz.structs.partition import WiaPartition


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

        except BaseException:
            self.file.close()
            raise


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

    def __enter__(self) -> "WiaReader":
        return self

    def __exit__(self, *args) -> None:
        self.close()