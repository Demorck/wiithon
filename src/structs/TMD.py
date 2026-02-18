from typing import List

from Enums import SignatureType
from structs.TMDContent import TMDContent
from Utils import *

class TMD:
    """
    See this: https://wiibrew.org/wiki/Title_metadata
    TODO: Change this comment to use actual structure
    ----------------------------------------- Signed Blob Header
    Offset  Taille          Field
    0x000   0x04            Signature Type
    0x004   0x100           Signature
    0x104   0x3C            60 bytes of padding
    ------------------------------------------- Main Header
    0x140   0x40            Signature issuer
    0x180   0x3C            ECDH data (Elliptic Curve Diffie-Hellman)
    0x1BD   0x01            Ticket format version
	0x1BD	0x02			Reserved
	0x1BF	0x10			Title Key, encrypted by Common Key
	0x1CF	0x01			Unknown
	0x1D0	0x08			ticket_id (used as IV for title key decryption of console specific titles)
	0x1D8	0x04			Console ID (NG ID in console specific titles)
	0x1DC	0x08			Title ID / Initialization Vector (IV) used for AES-CBC encryption
	0x1E4	0x02			Unknown, mostly 0xFFFF
	0x1E6	0x02			Ticket title version
	0x1E8	0x04			Permitted Titles Mask
	0x1EC	0x04			Permit mask. The current disc title is ANDed with the inverse of this mask to see if the result matches the Permitted Titles Mask.
	0x1F0	0x01			Title Export allowed using PRNG key (1 = allowed, 0 = not allowed)
	0x1F1	0x01			Common Key index (2 = Wii U Wii mode, 1 = Korean Common key, 0 = "normal" Common key)
	0x1F2	0x3			    Unknown. Is all 0 for non-VC, for VC, all 0 except last byte is 1.
	0x1F5	0x2D			Unknown.
	0x222	0x40			Content access permissions (one bit for each content)
	0x262	0x02			Padding (Always 0)
	0x264	0x04			Limit type (0 = disable, 1 = time limit (minutes), 3 = disable, 4 = launch count limit)
	0x268	0x04			Maximum usage, depending on limit type
	0x26C	0x38			7 more ccLimit structs as above ({int type, max})
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