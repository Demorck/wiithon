from typing import BinaryIO

from wiithon.binary.reader import BinaryReader
from wiithon.crypto.layout import BLOCK_DATA_SIZE, BLOCK_SIZE, SHA1_SIZE
from wiithon.rvz.enums import WiaCompression, WiaDiscType
from wiithon.rvz.layout import COMPRESSOR_DATA_SIZE, DHEAD_SIZE


class WiaDisc:
    """
    Structure after the header, at offset 0x48, describing the whole disc
    """

    def __init__(self) -> None:
        """
        Constructor, initialized everything at default, none or unknown values
        """
        #: Type of disc stored in this image
        self.disc_type: WiaDiscType = WiaDiscType.UNKNOWN

        #: What every chunk is compressed to
        self.compression: WiaCompression = WiaCompression.NONE

        #: Level given by the compressor, signed
        self.compression_level: int = 0

        #: Size of one chunk of data. WIA: multiple of 2MiB. RVZ: Power of two with a min of 0x8000
        self.chunk_size: int = 0

        #: The first 0x80 bytes of the disc image
        self.disc_head: bytes = b'\x00' * DHEAD_SIZE

        #: Number of partition struct
        self.partition_count: int = 0

        #: Size of one partition structure
        self.partition_struct_size: int = 0

        #: Where the struct is, uncompressed
        self.partition_offset: int = 0

        #: SHA1 hash of the partition structure. Number of bytes to hash: ``partition_count * partition_struct_size``
        self.partition_hash: bytes = b'\x00' * SHA1_SIZE

        #: Number of raw_data struct
        self.raw_data_count: int = 0

        #: Where the struct is, compressed
        self.raw_data_offset: int = 0

        #: Size of one raw_data structure
        self.raw_data_struct_size: int = 0

        #: Number of group structures
        self.group_count: int = 0

        #: Where the struct is, compressed
        self.group_offset: int = 0

        #: Size of the group structures
        self.group_size: int = 0

        #: Compressor specific data. Empty for NONE, PURGE, BZIP2 and ZSTD
        self.compression_data: bytes = b''

    @property
    def partition_chunk_size(self) -> int:
        """
        Payload of one group of partition data, hashes excluded

        Returns:
            The number of usable bytes a partition group have
        """
        return self.chunk_size // BLOCK_SIZE * BLOCK_DATA_SIZE

    @classmethod
    def read(cls, stream: BinaryIO) -> 'WiaDisc':
        """
        Read and validate the disc structure

        Args:
            stream: Current stream of the file

        Returns:
            The object created

        Raises:
            CorruptedDatError: If the hash does not match, the struct may be corrupted
        """
        obj = cls()

        reader = BinaryReader(stream)

        obj.disc_type = WiaDiscType(reader.u32())
        obj.compression = WiaCompression(reader.u32())
        obj.compression_level = reader.s32()
        obj.chunk_size = reader.u32()
        obj.disc_head = reader.raw(DHEAD_SIZE)
        obj.partition_count = reader.u32()
        obj.partition_struct_size = reader.u32()
        obj.partition_offset = reader.u64()
        obj.partition_hash = reader.raw(SHA1_SIZE)
        obj.raw_data_count = reader.u32()
        obj.raw_data_offset = reader.u64()
        obj.raw_data_struct_size = reader.u32()
        obj.group_count = reader.u32()
        obj.group_offset = reader.u64()
        obj.group_size = reader.u32()

        length = reader.u8()
        obj.compression_data      = reader.raw(COMPRESSOR_DATA_SIZE)[:length]

        return obj