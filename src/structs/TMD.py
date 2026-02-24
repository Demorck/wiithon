from typing import List

from structs.TMDContent import TMDContent
from helpers.Utils import *

"""
See this: https://wiibrew.org/wiki/Title_metadata
----------------------------------------- Signed Blob Header
Offset  Taille          Field
0x000   0x04            Signature Type
0x004   0x100           Signature
0x104   0x3C            60 bytes of padding
------------------------------------------- Main Header
0x140   0x40            Certificate issuer
0x180   0x01            Version
0x181   0x01            Ca_crl_version
0x182   0x01            signer_crl_version
0x183   0x01            Is Virtual wii (1 for vWii titles, 0 for normal titles)
0x184   0x08            System version
0x18C   0x08            Title ID
0x194   0x08            Title type
0x198   0x04            Group ID
0x19A   0x02            Zero
0x19C   0x02            Region (0: Japan, 1: USA, 2: Europe, 3: Region Free, 4: Korea)
0x19E   0x02            Ratings
0x1AE   0x10            Reserved
0x1BA   0x0C            IPC Mask
0x1C6   0x0C            Reserved
0x1D8   0x04            Access rights
0x1DC   0x02            Title version
0x1DE   0x02            Number of contents
0x1E0   0x02            boot index
0x1E2   0x02            Minor version (unused)
"""

class TMD:
    """
        Title Metadata for a Wii partition

        References:
            https://wiibrew.org/wiki/Title_metadata

        Attributes:
            signature_type   : RSA signature type
            signature        : RSA signature
            signature_issuer : Issuer (Like "Root-CA00000001-CP00000004")
            version            : TMD format version
            ca_crl_version     : CA Certificate Revocation List version
            signer_crl_version : Signer CRL version
            is_virtual_wii     : vWii flag
            system_version     : Required system version (IOS)
            title_id           : Title identifier (8 bytes, u64)
            title_type         : Title type
            group_id           : Group identifier
            access_flags       : Access flags
            title_version      : Title version
            num_contents       : Number of CMD entries
            boot_index         : Startup content index
            contents           : List of TMDContent
        """
    def __init__(self):
        self.signature_type: SignatureType = SignatureType.NONE
        self.signature: bytes = b'\x00' * 0x100
        self.signature_issuer: bytes = b'\x00' * 0x40
        self.version: int = 0
        self.ca_crl_version: int = 0
        self.signer_crl_version: int = 0
        self.is_virtual_wii: int = 0
        self.system_version: int = 0
        self.title_id: int = 0
        self.title_type: int = 0
        self.group_id: int = 0
        self.fake_signature_padding: bytes = b'\x00' * 0x38
        self.access_flags: int = 0
        self.title_version: int = 0
        self.num_contents: int = 0
        self.boot_index: int = 0
        self.contents: List[TMDContent] = []

    @classmethod
    def read(cls, stream: BinaryIO) -> "TMD":
        """
        Read and parse a Title metadata from a binary stream

        :param stream: Binary IO stream
        :return: TMD
        """
        obj = cls()

        obj.signature_type         = SignatureType(read_u32(stream))
        obj.signature              = stream.read(0x100)
        stream.read(0x3C)
        obj.signature_issuer       = stream.read(0x40)
        obj.version                = read_u8(stream)
        obj.ca_crl_version         = read_u8(stream)
        obj.signer_crl_version     = read_u8(stream)
        obj.is_virtual_wii         = read_u8(stream)
        obj.system_version         = read_u64(stream)
        obj.title_id               = read_u64(stream)
        obj.title_type             = read_u32(stream)
        obj.group_id               = read_u16(stream)
        obj.fake_signature_padding = stream.read(0x38)  # 7 x u64 = 8*7 = 56
        stream.read(0x06)
        obj.access_flags           = read_u32(stream)
        obj.title_version          = read_u16(stream)
        obj.num_contents           = read_u16(stream)
        obj.boot_index               = read_u16(stream)
        stream.read(0x02)
        obj.contents = [TMDContent.read(stream) for _ in range(obj.num_contents)]

        return obj

    def write(self, stream: BinaryIO) -> None:
        """
        Write content to a binary stream

        :param stream: Binary IO stream
        :return: None
        """
        self.num_contents = len(self.contents)

        stream.write(struct.pack('>I', self.signature_type))
        stream.write(self.signature)
        stream.write(b'\x00' * 0x3C)
        stream.write(self.signature_issuer)
        stream.write(struct.pack('>B', self.version))
        stream.write(struct.pack('>B', self.ca_crl_version))
        stream.write(struct.pack('>B', self.signer_crl_version))
        stream.write(struct.pack('>B', self.is_virtual_wii))
        stream.write(struct.pack('>Q', self.system_version))
        stream.write(struct.pack('>Q', self.title_id))
        stream.write(struct.pack('>I', self.title_type))
        stream.write(struct.pack('>H', self.group_id))
        stream.write(self.fake_signature_padding)
        stream.write(b'\x00' * 0x06)
        stream.write(struct.pack('>I', self.access_flags))
        stream.write(struct.pack('>H', self.title_version))
        stream.write(struct.pack('>H', self.num_contents))
        stream.write(struct.pack('>H', self.boot_index))
        stream.write(b'\x00' * 0x02)
        for content in self.contents:
            content.write(stream)