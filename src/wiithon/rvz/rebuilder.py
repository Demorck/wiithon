from typing import BinaryIO

from wiithon.crypto.blocks import encrypt_group_data, hash_group
from wiithon.crypto.layout import (
    BLOCK_DATA_SIZE,
    BLOCK_HEADER_SIZE,
    BLOCK_PER_GROUP,
    BLOCK_SIZE,
    GROUP_DATA_SIZE,
    GROUP_SIZE,
    SHA1_SIZE,
)
from wiithon.rvz.reader import WiaReader
from wiithon.rvz.structs.exception_list import WiaExceptionList


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
                stream.write(self.reader.read_group(group_index))

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
        if self.reader.disc.chunk_size < GROUP_SIZE:
            raise NotImplementedError(
                "Rebuilding from chunks smaller than a hash group is not supported yet"
            )

        blocks_per_chunk = self.reader.disc.chunk_size // BLOCK_SIZE
        for partition in self.reader.partitions:
            for segment in partition.segments:
                for i in range(segment.group_count):
                    lists, payload = self.reader.read_partition_group(segment.group_index + i)

                    for j, exceptions in enumerate(lists):
                        first_block = i * blocks_per_chunk + j * BLOCK_PER_GROUP
                        blocks = min(BLOCK_PER_GROUP, segment.block_count - first_block)
                        if blocks <= 0:
                            break

                        group = self._build_group(
                            payload[j * GROUP_DATA_SIZE: (j + 1) * GROUP_DATA_SIZE],
                            exceptions,
                        )
                        stream.seek(segment.offset + first_block * BLOCK_SIZE)
                        stream.write(
                            encrypt_group_data(group, partition.title_key)[:blocks * BLOCK_SIZE]
                        )

    @staticmethod
    def _build_group(payload: bytes, wia_exceptions: WiaExceptionList) -> bytearray:
        """
        Build and hash a group from the payload

        Args:
            payload: Up to ``GROUP_DATA_SIZE`` bytes of decrypted data
            wia_exceptions: Differences to apply once the hashes are computed

        Returns:
            A full group, hashed but not encrypted yet
        """
        buffer = bytearray(GROUP_SIZE)
        for block in range(BLOCK_PER_GROUP):
            source = payload[block * BLOCK_DATA_SIZE:(block + 1) * BLOCK_DATA_SIZE]
            start = block * BLOCK_SIZE + BLOCK_HEADER_SIZE
            buffer[start: start + len(source)] = source

        hash_group(buffer)

        for exceptions in wia_exceptions.exceptions:
            start = exceptions.block * BLOCK_SIZE + exceptions.offset_in_block
            buffer[start:start + SHA1_SIZE] = exceptions.hash

        return buffer