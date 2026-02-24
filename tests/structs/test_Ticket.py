import struct
import unittest
from io import BytesIO

from helpers.Enums import SignatureType
from structs.Ticket import Ticket


class TestTicket(unittest.TestCase):
    """Unit tests for Ticket read/write"""

    def _build_raw_ticket(self) -> bytes:
        """Build a fake raw ticket binary for testing"""
        buf = BytesIO()

        sig_type = SignatureType.RSA_2048
        buf.write(struct.pack('>I', sig_type))       
        buf.write(b'\xAA' * 0x100)                   
        buf.write(b'\x00' * 60)                      
        buf.write(b'Root-CA00000001-XS00000003\x00'.ljust(0x40, b'\x00'))  
        buf.write(b'\xBB' * 0x3C)                    
        buf.write(b'\x00' * 3)                       
        buf.write(b'\xCC' * 16)                      
        buf.write(b'\x00' * 1)                       
        buf.write(b'\x11' * 8)                       
        buf.write(b'\x22' * 4)                       
        buf.write(b'\x00\x01\x00\x00' + b'\x00' * 4)  
        buf.write(struct.pack('>H', 0))              
        buf.write(struct.pack('>H', 1))              
        buf.write(struct.pack('>I', 0xFFFFFFFF))     
        buf.write(struct.pack('>I', 0))              
        buf.write(struct.pack('>B', 0))              
        buf.write(struct.pack('>B', 0))              
        buf.write(b'\x00' * 48)                      
        buf.write(b'\xFF' * 0x40)                    
        buf.write(struct.pack('>H', 0))              
        for _ in range(8):                           
            buf.write(struct.pack('>II', 0, 0))

        return buf.getvalue()

    def test_read_fields(self) -> None:
        """Test that all fields are correctly parsed"""
        raw = self._build_raw_ticket()
        ticket = Ticket.read(BytesIO(raw))

        self.assertEqual(ticket.signature_type, SignatureType.RSA_2048)
        self.assertEqual(ticket.signature, b'\xAA' * 0x100)
        self.assertEqual(ticket.ecdh, b'\xBB' * 0x3C)
        self.assertEqual(ticket.encrypted_key, b'\xCC' * 16)
        self.assertEqual(ticket.ticket_id, b'\x11' * 8)
        self.assertEqual(ticket.console_id, b'\x22' * 4)
        self.assertEqual(ticket.ticket_version, 1)
        self.assertEqual(ticket.common_key_index, 0)
        self.assertEqual(len(ticket.time_limit), 8)

    def test_title_key_is_decrypted(self) -> None:
        """Test that the title key is decrypted (not equal to encrypted_key)"""
        raw = self._build_raw_ticket()
        ticket = Ticket.read(BytesIO(raw))

        
        self.assertNotEqual(ticket.title_key, ticket.encrypted_key)
        
        self.assertEqual(len(ticket.title_key), 16)

    def test_roundtrip(self) -> None:
        """Test that read -> write -> read produces identical results."""
        raw = self._build_raw_ticket()
        ticket1 = Ticket.read(BytesIO(raw))
        
        out = BytesIO()
        ticket1.write(out)
        
        out.seek(0)
        ticket2 = Ticket.read(out)
        
        self.assertEqual(ticket1.signature_type, ticket2.signature_type)
        self.assertEqual(ticket1.signature, ticket2.signature)
        self.assertEqual(ticket1.title_key, ticket2.title_key)
        self.assertEqual(ticket1.title_id, ticket2.title_id)
        self.assertEqual(ticket1.ticket_version, ticket2.ticket_version)
        self.assertEqual(ticket1.common_key_index, ticket2.common_key_index)


if __name__ == "__main__":
    unittest.main()