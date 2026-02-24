import struct
import unittest
from io import BytesIO

from structs.Certificate import Certificate
from helpers.Enums import SignatureType, KeyType


class TestCertificate(unittest.TestCase):
    """Unit tests for Certificate."""

    def _build_raw_cert(self, sig_type: SignatureType = SignatureType.RSA_2048,
                        key_type: KeyType = KeyType.RSA_2048) -> bytes:
        """Build raw binary data for a certificate.
        """
        buf = BytesIO()

        # Signature header
        buf.write(struct.pack('>I', sig_type))
        if sig_type == SignatureType.RSA_4096:
            buf.write(b'\xAA' * 512)
        elif sig_type == SignatureType.RSA_2048:
            buf.write(b'\xAA' * 256)
        elif sig_type == SignatureType.ELLIPSIS:
            buf.write(b'\xAA' * 64)
        buf.write(b'\x00' * 0x3C)  # padding 60

        # Certificate data
        buf.write(b'Root-CA00000001\x00'.ljust(0x40, b'\x00'))  # issuer
        buf.write(struct.pack('>I', key_type))
        buf.write(b'CP00000004\x00'.ljust(0x40, b'\x00'))  # child_identity
        buf.write(struct.pack('>I', 0x12345678))  # key_id

        # Public key section
        if key_type == KeyType.RSA_4096:
            buf.write(b'\xBB' * 0x200)           # 512 bytes key
            buf.write(struct.pack('>I', 65537))   # public_exponent
            buf.write(b'\x00' * 0x34)             # padding 52
        elif key_type == KeyType.RSA_2048:
            buf.write(b'\xCC' * 0x100)            # 256 bytes key
            buf.write(struct.pack('>I', 65537))   # public_exponent
            buf.write(b'\x00' * 0x34)             # padding 52
        elif key_type == KeyType.ECC_B233:
            buf.write(b'\xDD' * 60)               # 60 bytes key
            buf.write(b'\x00' * 60)               # padding 60

        return buf.getvalue()

    def test_read_rsa2048(self) -> None:
        """Test reading a certificate with RSA-2048 key."""
        raw = self._build_raw_cert(SignatureType.RSA_2048, KeyType.RSA_2048)
        cert = Certificate.read(BytesIO(raw))

        self.assertEqual(cert.signature_type, SignatureType.RSA_2048)
        self.assertEqual(len(cert.signature), 256)
        self.assertEqual(cert.signature, b'\xAA' * 256)
        self.assertEqual(cert.key_type, KeyType.RSA_2048)
        self.assertEqual(cert.key_id, 0x12345678)
        self.assertEqual(len(cert.key), 0x100)
        self.assertEqual(cert.key, b'\xCC' * 0x100)
        self.assertEqual(cert.public_exponent, 65537)

    def test_read_rsa4096(self) -> None:
        """Test reading a certificate with RSA-4096 key."""
        raw = self._build_raw_cert(SignatureType.RSA_2048, KeyType.RSA_4096)
        cert = Certificate.read(BytesIO(raw))

        self.assertEqual(cert.key_type, KeyType.RSA_4096)
        self.assertEqual(len(cert.key), 0x200)
        self.assertEqual(cert.key, b'\xBB' * 0x200)

    def test_roundtrip_rsa2048(self) -> None:
        """Test read → write → read roundtrip with RSA-2048."""
        raw = self._build_raw_cert(SignatureType.RSA_2048, KeyType.RSA_2048)
        cert1 = Certificate.read(BytesIO(raw))

        out = BytesIO()
        cert1.write(out)

        out.seek(0)
        cert2 = Certificate.read(out)

        self.assertEqual(cert1.signature_type, cert2.signature_type)
        self.assertEqual(cert1.signature, cert2.signature)
        self.assertEqual(cert1.issuer, cert2.issuer)
        self.assertEqual(cert1.key_type, cert2.key_type)
        self.assertEqual(cert1.child_identity, cert2.child_identity)
        self.assertEqual(cert1.key_id, cert2.key_id)
        self.assertEqual(cert1.key, cert2.key)
        self.assertEqual(cert1.public_exponent, cert2.public_exponent)

    def test_roundtrip_rsa4096(self) -> None:
        """Test read → write → read roundtrip with RSA-4096."""
        raw = self._build_raw_cert(SignatureType.RSA_4096, KeyType.RSA_4096)
        cert1 = Certificate.read(BytesIO(raw))

        out = BytesIO()
        cert1.write(out)

        out.seek(0)
        cert2 = Certificate.read(out)

        self.assertEqual(cert1.signature, cert2.signature)
        self.assertEqual(len(cert1.signature), 512)
        self.assertEqual(cert1.key, cert2.key)
        self.assertEqual(len(cert1.key), 512)


if __name__ == "__main__":
    unittest.main()