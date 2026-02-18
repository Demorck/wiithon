from Enums import SignatureType, KeyType
from Utils import *

class Certificate:
    """
    https://wiibrew.org/wiki/Certificate_chain
    """
    def __init__(self) -> None:
        self.signature_type: SignatureType = SignatureType.NONE
        self.signature: bytes = b'\x00'
        self.issuer: bytes = b'\x00' * 0x40
        self.key_type: KeyType = KeyType.NONE
        self.child_identity: bytes = b'\x00' * 0x40
        self.key_id: int = 0
        self.key: bytes = b'\x00'
        self.public_exponent: int = 0


    @classmethod
    def read(cls, stream: BinaryIO) -> "Certificate":
        obj = cls()

        obj.signature_type = SignatureType(read_u32(stream))
        length: int = 0
        if obj.signature_type == SignatureType.RSA_2048:
            length = 256
        elif obj.signature_type == SignatureType.RSA_4096:
            length = 512
        elif obj.signature_type == SignatureType.ELLIPSIS:
            length = 64

        obj.signature = stream.read(length)
        stream.read(0x3C)
        obj.issuer = stream.read(0x40)
        obj.key_type = KeyType(read_u32(stream))
        obj.child_identity = stream.read(0x40)
        obj.key_id = read_u32(stream)
        if obj.key_type == KeyType.RSA_2048:
            obj.key = stream.read(0x100)
            obj.public_exponent = read_u32(stream)
            stream.read(0x34)
        elif obj.key_type == KeyType.RSA_4096:
            obj.key = stream.read(0x200)
            obj.public_exponent = read_u32(stream)
            stream.read(0x34)
        elif obj.key_type == KeyType.ECC_B233:
            obj.key = stream.read(0x3C)
            stream.read(0x60)

        return obj

    def write(self, stream: BinaryIO) -> None:
        stream.write(struct.pack('>I', self.signature_type))
        stream.write(self.signature)
        stream.write(b'\x00' * 0x3C)
        stream.write(self.issuer)
        stream.write(struct.pack('>I', self.key_type))
        stream.write(self.child_identity)
        stream.write(struct.pack('>I', self.key_id))
        stream.write(self.key)

        if self.key_type in (KeyType.RSA_4096, KeyType.RSA_2048):
            stream.write(struct.pack('>I', self.public_exponent))
            stream.write(b'\x00' * 0x34)
        else:
            stream.write(b'\x00' * 60)