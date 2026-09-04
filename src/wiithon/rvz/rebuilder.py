from typing import BinaryIO

from wiithon.crypto.blocks import encrypt_group_data, hash_group
from wiithon.crypto.layout import (
    BLOCK_DATA_SIZE,
    BLOCK_HEADER_SIZE,
    BLOCK_PER_GROUP,
    BLOCK_SIZE,
    GROUP_SIZE,
    SHA1_SIZE,
)
from wiithon.rvz.reader import WiaReader
from wiithon.rvz.structs.exception_list import WiaExceptionList
from wiithon.rvz.structs.partition_data import WiaPartitionData


class IsoRebuilder:
    """
    Rebuilds the disc image from a WIA/RVZ
    """

    def __init__(self, reader: WiaReader) -> None:
        """
        Constructor

        Args:
            reader: WIA/RVZ opened
        """
        #: The WIA/RVZ Reader
        self.reader = reader

    def write_raw_data(self, stream: BinaryIO) -> None:
        """
        Wrtie every data of the disc that lives outside a partition

        Args:
            stream: Where to write (opened for writing/seeking)
        """
        chunk = self.reader.disc.chunk_size
        stream.truncate(self.reader.header.iso_file_size)

        for entry in self.reader.raw_data:
            for i in range(entry.group_count):
                group_index = entry.first_group_index + i
                if self.reader.groups[group_index].is_zero:
                    continue

                stream.seek(entry.offset + i * chunk)
                stream.write(self.reader.read_raw_group(entry, i))

    def write(self, stream: BinaryIO) -> None:
        """
        Rebuild the whole image

        Args:
            stream: Where to write, opened for writing and seeking
        """
        self.write_raw_data(stream)
        self.write_partitions(stream)


    def write_partitions(self, stream: BinaryIO) -> None:
        """
        Write the encrypted data of every partition

        Args:
            stream: Where to write, opened for writing and seeking

        Raises:
            NotImplementedError: If a chunk is smaller than a hash group
        """
        for partition in self.reader.partitions:
            first_block = partition.segments[0].first_block
            for segment in partition.segments:
                self._write_segment(stream, segment, partition.title_key, first_block)

    def _write_segment(
            self,
            stream: BinaryIO,
            segment: WiaPartitionData,
            title_key: bytes,
            partition_first_block: int
    ) -> None:
        """
        Write one segment of a partition at a time

        Args:
            stream: Where to write, opened for writing/seeking as always
            segment: The segment to write
            title_key: Decrypted key
        """
        blocks_per_chunk = self.reader.disc.chunk_size // BLOCK_SIZE
        blocks_per_list = min(blocks_per_chunk, BLOCK_PER_GROUP)

        buffer = bytearray(GROUP_SIZE)
        patches: list[tuple[int, WiaExceptionList]] = []
        first_block_of_group = 0

        for i in range(segment.group_count):
            block = segment.first_block - partition_first_block + i * blocks_per_chunk
            lists, payload = self.reader.read_partition_group(
                segment.group_index + i, block * BLOCK_DATA_SIZE
            )

            for k, exceptions in enumerate(lists):
                first_block = i * blocks_per_chunk + k * blocks_per_list
                if first_block >= segment.block_count:
                    break

                base = first_block - first_block_of_group
                start = k * blocks_per_list * BLOCK_DATA_SIZE
                self._place(buffer, base, payload[start:start + blocks_per_list * BLOCK_DATA_SIZE])
                patches.append((base, exceptions))

                if base + blocks_per_list < BLOCK_PER_GROUP:
                    continue

                self._write_group(
                    stream,
                    segment.offset + first_block_of_group * BLOCK_SIZE,
                    min(BLOCK_PER_GROUP, segment.block_count - first_block_of_group),
                    buffer, patches, title_key,
                )
                first_block_of_group += BLOCK_PER_GROUP
                buffer, patches = bytearray(GROUP_SIZE), []

        blocks = segment.block_count - first_block_of_group
        if blocks > 0:
            self._write_group(
                stream,
                segment.offset + first_block_of_group * BLOCK_SIZE,
                blocks, buffer, patches, title_key,
            )

    @staticmethod
    def _place(buffer: bytearray, first_block: int, payload: bytes) -> None:
        """
        Copy a payload into the data area of consecutive blocks of a group

        Args:
            buffer: The group being assembled
            first_block: Which blcok of the group the payload start at
            payload: Decrypted data, without the hash
        """
        for offset in range(0, len(payload), BLOCK_DATA_SIZE):
            piece = payload[offset:offset + BLOCK_DATA_SIZE]
            at = (first_block + offset // BLOCK_DATA_SIZE) * BLOCK_SIZE + BLOCK_HEADER_SIZE
            buffer[at:at + len(piece)] = piece

    @staticmethod
    def _write_group(
            stream: BinaryIO,
            offset: int,
            blocks: int,
            buffer: bytearray,
            patches: list[tuple[int, WiaExceptionList]],
            title_key: bytes
    ) -> None:
        """
        Hash a group, encrypt it and write it

        Args:
            stream: Where to write, opened for writing/seeking as always
            offset: Where the group starts of the disc
            blocks: How many blocks of it the segment holds
            buffer: The assembled group
            patches: Exception lists
            title_key: Decrypted key
        """
        hash_group(buffer)

        for base, exceptions_list in patches:
            for exception in exceptions_list.exceptions:
                at = (base + exception.block) * BLOCK_SIZE + exception.offset_in_block
                buffer[at:at + SHA1_SIZE] = exception.hash

        stream.seek(offset)
        stream.write(
            encrypt_group_data(buffer, title_key)[:blocks * BLOCK_SIZE]
        )