from typing import BinaryIO

from helpers.Utils import read_u32, read_u64_shifted
from structs.Ticket import Ticket
import struct


class WiiPartitionHeader:
    """
    https://wiibrew.org/wiki/Wii_disc#Partition
    """
    def __init__(self):
        self.ticket: Ticket|None = None
        self.tmd_size: int = 0
        self.tmd_offset: int = 0
        self.certificate_chain_size: int = 0
        self.certificate_chain_offset: int = 0
        self.global_hash_table_offset: int = 0
        self.data_offset: int = 0
        self.data_size: int = 0


    @classmethod
    def read(cls, stream: BinaryIO) -> "WiiPartitionHeader":
        """
        Read a partition header
        :param stream:
        :return:
        """
        obj = cls()

        obj.ticket                   = Ticket.read(stream)
        obj.tmd_size                 = read_u32(stream)
        obj.tmd_offset               = read_u64_shifted(stream)
        obj.certificate_chain_size   = read_u32(stream)
        obj.certificate_chain_offset = read_u64_shifted(stream)
        obj.global_hash_table_offset = read_u64_shifted(stream)
        obj.data_offset              = read_u64_shifted(stream)
        obj.data_size                = read_u64_shifted(stream)

        return obj

    def write(self, stream: BinaryIO) -> None:
        """
        Write a partition header
        :param stream:
        :return:
        """
        self.ticket.write(stream)
        stream.write(struct.pack('>I', self.tmd_size))
        stream.write(struct.pack('>I', self.tmd_offset >> 2))
        stream.write(struct.pack('>I', self.certificate_chain_size))
        stream.write(struct.pack('>I', self.certificate_chain_offset >> 2))
        stream.write(struct.pack('>I', self.global_hash_table_offset >> 2))
        stream.write(struct.pack('>I', self.data_offset >> 2))
        stream.write(struct.pack('>I', self.data_size >> 2))