from typing import BinaryIO
from Utils import read_u8, read_u32, read_string, read_u64_shifted
import struct

class DiscHeader:
    """
    https://wiibrew.org/wiki/Wii_disc#Header
    and
    https://wiibrew.org/wiki/Wii_disc#Decrypted
    """
    def __init__(self):
        self.game_id: bytes = b'\x00' * 0x06
        self.disc_num: int = 0
        self.disc_version: int = 0
        self.audio_streaming: int = 0
        self.audio_stream_buf_size: int = 0
        self.wii_magic_word: int = 0
        self.gamecube_magic_word: int = 0
        self.game_title: str = ""
        self.disable_hash_verification: int = 0
        self.disable_disc_encryption: int = 0


        self.debug_mon_offset: int = 0
        self.debug_load_address: int = 0
        self.DOL_offset: int = 0
        self.FST_offset: int = 0
        self.FST_size: int = 0
        self.FST_max_size: int = 0
        self.FST_memory_address: int = 0
        self.user_position: int = 0
        self.user_size: int = 0


    @classmethod
    def read(cls, stream: BinaryIO) -> 'DiscHeader':
        """
        Read a disc header
        :param stream:
        :return:
        """
        obj = cls()

        obj.game_id = stream.read(0x06)

        obj.disc_num = read_u8(stream)
        obj.disc_version = read_u8(stream)
        obj.audio_streaming = read_u8(stream)
        obj.audio_stream_buf_size = read_u8(stream)
        stream.read(0x0E)
        obj.wii_magic_word = read_u32(stream)
        obj.gamecube_magic_word = read_u32(stream)
        obj.game_title = read_string(stream, 0x40)
        obj.disable_hash_verification = read_u8(stream)
        obj.disable_disc_encryption = read_u8(stream)
        stream.read(0x39E)
        obj.debug_mon_offset = read_u32(stream)
        obj.debug_load_address = read_u32(stream)
        stream.read(0x18)
        obj.DOL_offset = read_u64_shifted(stream)
        obj.FST_offset = read_u64_shifted(stream)
        obj.FST_size = read_u64_shifted(stream)
        obj.FST_max_size = read_u64_shifted(stream)
        obj.FST_memory_address =  read_u32(stream)
        obj.user_position =  read_u32(stream)
        obj.user_size =  read_u32(stream)
        stream.read(0x04)

        return obj

    def write(self, stream: BinaryIO) -> None:
        """
        Write a disc header
        :param stream:
        :return:
        """
        stream.write(self.game_id)
        stream.write(struct.pack('>B', self.disc_num))
        stream.write(struct.pack('>B', self.disc_version))
        stream.write(struct.pack('>B', self.audio_streaming))
        stream.write(struct.pack('>B', self.audio_stream_buf_size))
        stream.write(b'\x00' * 0x0E)
        stream.write(struct.pack('>I', self.wii_magic_word))
        stream.write(struct.pack('>I', self.gamecube_magic_word))
        stream.write(self.game_title.encode('ascii').ljust(0x40, b'\x00'))
        stream.write(struct.pack('>B', self.disable_hash_verification))
        stream.write(struct.pack('>B', self.disable_disc_encryption))
        stream.write(b'\x00' * 0x39E)
        stream.write(struct.pack('>I', self.debug_mon_offset))
        stream.write(struct.pack('>I', self.debug_load_address))
        stream.write(b'\x00' * 0x18)
        stream.write(struct.pack('>I', self.DOL_offset >> 2))
        stream.write(struct.pack('>I', self.FST_offset >> 2))
        stream.write(struct.pack('>I', self.FST_size >> 2))
        stream.write(struct.pack('>I', self.FST_max_size >> 2))
        stream.write(struct.pack('>I', self.FST_memory_address))
        stream.write(struct.pack('>I', self.user_position))
        stream.write(struct.pack('>I', self.user_size))
        stream.write(b'\x00' * 0x04)




