from typing import BinaryIO

from helpers.Constants import GROUP_SIZE, GROUP_DATA_SIZE, BLOCK_SIZE, BLOCK_HEADER_SIZE, BLOCK_DATA_SIZE, \
    BLOCk_PER_GROUP, SHA1_SIZE
from helpers.Utils import encrypt_group


class CryptPartWriter:
    """
    Writes data into a Wii partition and encrypting
    """
    def __init__(self, stream: BinaryIO, data_offset: int, title_key: bytes) -> None:
        """
        :param stream: Open stream in write mode
        :param data_offset: Absolute offset of partition data in the ISO
        :param title_key: 16-byte decrypted title key
        """
        self.stream = stream
        self.data_offset = data_offset
        self.title_key = title_key
        
        self.current_position: int = 0
        self.buffer = bytearray(GROUP_DATA_SIZE)
        self.buffer_size: int = 0
        self.h3_table = bytearray()
        self.filled_groups: int = 0

    def write(self, data: bytes) -> None:
        """
        Write decrypted data to the partition
        :param data: Data to write
        """
        data_len = len(data)
        offset = 0
        
        while offset < data_len:
            space_left = GROUP_DATA_SIZE - self.buffer_size
            chunk_size = min(space_left, data_len - offset)
            
            self.buffer[self.buffer_size : self.buffer_size + chunk_size] = data[offset : offset + chunk_size]
            self.buffer_size += chunk_size
            self.current_position += chunk_size
            offset += chunk_size
            
            if self.buffer_size == GROUP_DATA_SIZE:
                self._flush_group()

    def _flush_group(self) -> None:
        """
        Encrypt the current buffer and write it to the stream
        """
        if self.buffer_size == 0:
            return
            
        if self.buffer_size < GROUP_DATA_SIZE:
            self.buffer[self.buffer_size:] = b'\x00' * (GROUP_DATA_SIZE - self.buffer_size)

        raw_group = bytearray(GROUP_SIZE)

        for i in range(BLOCk_PER_GROUP):
            raw_block_start = i * BLOCK_SIZE
            data_block_start = i * BLOCK_DATA_SIZE
            raw_group[raw_block_start + BLOCK_HEADER_SIZE : raw_block_start + BLOCK_SIZE] = self.buffer[data_block_start : data_block_start + BLOCK_DATA_SIZE]

        h3_hash = bytearray(SHA1_SIZE)
        encrypted_group = encrypt_group(raw_group, self.title_key, h3_hash)

        self.h3_table.extend(h3_hash)

        self.stream.seek(self.data_offset + self.filled_groups * GROUP_SIZE)
        self.stream.write(encrypted_group)

        self.filled_groups += 1
        self.buffer_size = 0

    def get_h3_table(self) -> bytes:
        """
        Get the concatenated H3 hashes for all groups
        """
        padding_needed = 0x18000 - len(self.h3_table)
        if padding_needed > 0:
            return bytes(self.h3_table) + (b'\x00' * padding_needed)
        return bytes(self.h3_table)

    def close(self) -> None:
        """
        Flush any remaining data and finish
        """
        self._flush_group()
