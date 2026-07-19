import struct
import unittest
from io import BytesIO

from wiithon.file_helper.dol import DOL, HEADER_SIZE, DATA_SECTIONS, TEXT_SECTIONS
from wiithon.structs.DOLHeader import DOLHeader


def build_mock_dol(text_data: bytes = b'\x60\x00\x00\x00' * 4,
                   text_start: int = 0x80003100) -> bytes:
    out = BytesIO()

    header = DOLHeader()
    header.text_offset = [HEADER_SIZE] + [0] * 6
    header.text_starts = [text_start] + [0] * 6
    header.text_length = [len(text_data)] + [0] * 6
    header.data_offset = [0] * 11
    header.data_starts = [0] * 11
    header.data_length = [0] * 11
    header.bss_start   = 0
    header.bss_size    = 0
    header.entry_point = text_start

    header.write(out)
    out.write(text_data)

    return out.getvalue()


class TestDOLRead(unittest.TestCase):

    def test_read_sections(self):
        text_data = b'\xAB\xCD\xEF\x00' * 4
        raw = build_mock_dol(text_data)
        dol = DOL.read(BytesIO(raw))

        self.assertEqual(dol.text_sections[0], text_data)
        for i in range(1, 7):
            self.assertEqual(dol.text_sections[i], b'')
        for i in range(11):
            self.assertEqual(dol.data_sections[i], b'')

    def test_entry_point(self):
        raw = build_mock_dol(text_start=0x80003100)
        dol = DOL.read(BytesIO(raw))
        self.assertEqual(dol.header.entry_point, 0x80003100)


class TestDOLReadAt(unittest.TestCase):

    def setUp(self):
        self.text_data = b'\x38\x60\x00\x01' * 4
        self.text_start = 0x80003100
        raw = build_mock_dol(self.text_data, self.text_start)
        self.dol = DOL.read(BytesIO(raw))

    def test_read_first_instruction(self):
        result = self.dol.read_at(self.text_start, 4)
        self.assertEqual(result, b'\x38\x60\x00\x01')

    def test_read_middle(self):
        result = self.dol.read_at(self.text_start + 8, 4)
        self.assertEqual(result, b'\x38\x60\x00\x01')

    def test_read_multiple_instructions(self):
        result = self.dol.read_at(self.text_start, 8)
        self.assertEqual(result, b'\x38\x60\x00\x01' * 2)

    def test_read_invalid_address(self):
        with self.assertRaises(ValueError):
            self.dol.read_at(0x80000000, 4)

    def test_read_overflow(self):
        with self.assertRaises(ValueError):
            self.dol.read_at(self.text_start, len(self.text_data) + 4)


class TestDOLWriteAt(unittest.TestCase):

    def setUp(self):
        self.text_data = b'\x60\x00\x00\x00' * 4
        self.text_start = 0x80003100
        raw = build_mock_dol(self.text_data, self.text_start)
        self.dol = DOL.read(BytesIO(raw))

    def test_write_single_instruction(self):
        new_instr = b'\x38\x60\x00\x01'
        self.dol.write_at(self.text_start, new_instr)
        self.assertEqual(self.dol.read_at(self.text_start, 4), new_instr)

    def test_write_does_not_affect_neighbours(self):
        self.dol.write_at(self.text_start + 4, b'\x38\x60\x00\x02')
        self.assertEqual(self.dol.read_at(self.text_start, 4), b'\x60\x00\x00\x00')

    def test_write_invalid_address(self):
        with self.assertRaises(ValueError):
            self.dol.write_at(0x90000000, b'\x60\x00\x00\x00')

    def test_write_overflow(self):
        with self.assertRaises(ValueError):
            self.dol.write_at(self.text_start, b'\x00' * (len(self.text_data) + 4))


class TestDOLToBytes(unittest.TestCase):

    def test_roundtrip(self):
        text_data = b'\x38\x60\x00\x01' * 4
        raw = build_mock_dol(text_data, 0x80003100)
        dol = DOL.read(BytesIO(raw))

        rebuilt = dol.to_bytes()
        dol2 = DOL.read(BytesIO(rebuilt))

        self.assertEqual(dol2.text_sections[0], text_data)
        self.assertEqual(dol2.header.entry_point, 0x80003100)
        self.assertEqual(dol2.header.text_starts[0], 0x80003100)

    def test_roundtrip_after_patch(self):
        text_data = b'\x60\x00\x00\x00' * 4
        raw = build_mock_dol(text_data, 0x80003100)
        dol = DOL.read(BytesIO(raw))

        dol.write_at(0x80003100, b'\x38\x60\x00\x01')  # patch nop -> li r3, 1

        rebuilt = dol.to_bytes()
        dol2 = DOL.read(BytesIO(rebuilt))

        self.assertEqual(dol2.read_at(0x80003100, 4), b'\x38\x60\x00\x01')
        self.assertEqual(dol2.read_at(0x80003104, 4), b'\x60\x00\x00\x00')

    def test_header_size_is_0x100(self):
        raw = build_mock_dol()
        dol = DOL.read(BytesIO(raw))
        rebuilt = dol.to_bytes()
        dol2 = DOL.read(BytesIO(rebuilt))
        self.assertEqual(dol2.header.text_offset[0], HEADER_SIZE)

class TestAddTextSection(unittest.TestCase):

    def setUp(self):
        raw = build_mock_dol(b'\x60\x00\x00\x00' * 4, text_start=0x80004000)
        self.dol = DOL.read(BytesIO(raw))
        self.inject_addr = 0x806AE000
        self.inject_data = b'\x38\x60\x00\x2A' * 4  # li r3, 42 x4

    def test_uses_first_free_slot(self):
        self.dol.add_text_section(self.inject_addr, self.inject_data)
        self.assertEqual(self.dol.text_sections[1], self.inject_data)

    def test_sets_virtual_address(self):
        self.dol.add_text_section(self.inject_addr, self.inject_data)
        self.assertEqual(self.dol.header.text_starts[1], self.inject_addr)

    def test_sets_length(self):
        self.dol.add_text_section(self.inject_addr, self.inject_data)
        self.assertEqual(self.dol.header.text_length[1], len(self.inject_data))

    def test_readable_via_read_at(self):
        self.dol.add_text_section(self.inject_addr, self.inject_data)
        result = self.dol.read_at(self.inject_addr, 4)
        self.assertEqual(result, b'\x38\x60\x00\x2A')

    def test_roundtrip_after_add(self):
        self.dol.add_text_section(self.inject_addr, self.inject_data)
        rebuilt = DOL.read(BytesIO(self.dol.to_bytes()))
        self.assertEqual(rebuilt.read_at(self.inject_addr, len(self.inject_data)), self.inject_data)

    def test_does_not_affect_existing_section(self):
        self.dol.add_text_section(self.inject_addr, self.inject_data)
        self.assertEqual(self.dol.read_at(0x80004000, 4), b'\x60\x00\x00\x00')

    def test_raises_when_all_slots_used(self):
        for i in range(TEXT_SECTIONS - 1):
            self.dol.add_text_section(0x80700000 + i * 0x1000, b'\x60\x00\x00\x00' * 4)
        with self.assertRaises(RuntimeError):
            self.dol.add_text_section(0x80800000, b'\x60\x00\x00\x00' * 4)


class TestAddDataSection(unittest.TestCase):

    def setUp(self):
        raw = build_mock_dol(b'\x60\x00\x00\x00' * 4, text_start=0x80004000)
        self.dol = DOL.read(BytesIO(raw))
        self.inject_addr = 0x806AE000
        self.inject_data = b'\xDE\xAD\xBE\xEF' * 4

    def test_uses_first_free_slot(self):
        self.dol.add_data_section(self.inject_addr, self.inject_data)
        self.assertEqual(self.dol.data_sections[0], self.inject_data)

    def test_sets_virtual_address(self):
        self.dol.add_data_section(self.inject_addr, self.inject_data)
        self.assertEqual(self.dol.header.data_starts[0], self.inject_addr)

    def test_sets_length(self):
        self.dol.add_data_section(self.inject_addr, self.inject_data)
        self.assertEqual(self.dol.header.data_length[0], len(self.inject_data))

    def test_readable_via_read_at(self):
        self.dol.add_data_section(self.inject_addr, self.inject_data)
        result = self.dol.read_at(self.inject_addr, 4)
        self.assertEqual(result, b'\xDE\xAD\xBE\xEF')

    def test_roundtrip_after_add(self):
        self.dol.add_data_section(self.inject_addr, self.inject_data)
        rebuilt = DOL.read(BytesIO(self.dol.to_bytes()))
        self.assertEqual(rebuilt.read_at(self.inject_addr, len(self.inject_data)), self.inject_data)
        self.assertEqual(self.dol.header.data_length[0], 4 * 0x4)

    def test_raises_when_all_slots_used(self):
        for i in range(DATA_SECTIONS):
            self.dol.add_data_section(0x80700000 + i * 0x1000, b'\x00' * 4)
        with self.assertRaises(RuntimeError):
            self.dol.add_data_section(0x80800000, b'\x00' * 4)


# arenaLo helpers

ARENA_SETTER_VADDR = 0x80003100


def _make_arena_pattern(arena_lo: int) -> bytes:
    """Builds the 16-byte arenaLo instruction sequence for a given value."""
    hi = (arena_lo >> 16) & 0xFFFF
    lo = arena_lo & 0xFFFF
    if lo >= 0x8000:
        hi = (hi + 1) & 0xFFFF

    w0 = struct.pack('>I', (15 << 26) | (3 << 21) | hi)           # lis  r3, hi
    w1 = struct.pack('>I', (14 << 26) | (3 << 21) | (3 << 16) | lo)  # addi r3, r3, lo
    w2 = bytes([0x38, 0x03, 0x00, 0x1f])                           # addi r0, r3, 31
    w3 = bytes([0x54, 0x03, 0x00, 0x18])                           # rlwinm r3, r0, …
    return w0 + w1 + w2 + w3


def build_mock_dol_with_arena(arena_lo: int = 0x80394E00) -> DOL:
    """DOL with the arenaLo pattern at ARENA_SETTER_VADDR, free slots for injection."""
    pattern = _make_arena_pattern(arena_lo)
    text_data = pattern + b'\x60\x00\x00\x00' * 16
    return DOL.read(BytesIO(build_mock_dol(text_data, ARENA_SETTER_VADDR)))


class TestFindArenaLoSetter(unittest.TestCase):

    def test_finds_pattern_at_section_start(self):
        dol = build_mock_dol_with_arena()
        self.assertEqual(dol.find_arena_lo_setter(), ARENA_SETTER_VADDR)

    def test_finds_pattern_after_nops(self):
        pattern = _make_arena_pattern(0x80394E00)
        text_data = b'\x60\x00\x00\x00' * 8 + pattern + b'\x60\x00\x00\x00' * 4
        dol = DOL.read(BytesIO(build_mock_dol(text_data, ARENA_SETTER_VADDR)))
        self.assertEqual(dol.find_arena_lo_setter(), ARENA_SETTER_VADDR + 8 * 4)

    def test_raises_when_pattern_absent(self):
        raw = build_mock_dol(b'\x60\x00\x00\x00' * 16)
        dol = DOL.read(BytesIO(raw))
        with self.assertRaises(RuntimeError):
            dol.find_arena_lo_setter()


class TestReadArenaLo(unittest.TestCase):

    def test_lo_below_8000(self):
        # MKWii: 0x80394E00 - lo = 0x4E00, no sign extension
        dol = build_mock_dol_with_arena(0x80394E00)
        self.assertEqual(dol.read_arena_lo(ARENA_SETTER_VADDR), 0x80394E00)

    def test_lo_above_8000_addi_sign_extends(self):
        # Skyward Sword: 0x806882C0 - lo = 0x82C0 >= 0x8000, addi sign-extends
        dol = build_mock_dol_with_arena(0x806882C0)
        self.assertEqual(dol.read_arena_lo(ARENA_SETTER_VADDR), 0x806882C0)

    def test_reads_ori_after_patch(self):
        # patch_arena_lo writes lis+ori; read_arena_lo must decode ori (unsigned)
        dol = build_mock_dol_with_arena(0x80394E00)
        dol.patch_arena_lo(ARENA_SETTER_VADDR, 0x80394E20)
        self.assertEqual(dol.read_arena_lo(ARENA_SETTER_VADDR), 0x80394E20)


class TestPatchArenaLo(unittest.TestCase):

    def setUp(self):
        self.dol = build_mock_dol_with_arena(0x80394E00)

    def test_roundtrip_lo_below_8000(self):
        self.dol.patch_arena_lo(ARENA_SETTER_VADDR, 0x80394F00)
        self.assertEqual(self.dol.read_arena_lo(ARENA_SETTER_VADDR), 0x80394F00)

    def test_roundtrip_lo_above_8000(self):
        self.dol.patch_arena_lo(ARENA_SETTER_VADDR, 0x806882E0)
        self.assertEqual(self.dol.read_arena_lo(ARENA_SETTER_VADDR), 0x806882E0)

    def test_second_instruction_is_ori(self):
        # Must write ori (opcode 24), not addi (opcode 14)
        self.dol.patch_arena_lo(ARENA_SETTER_VADDR, 0x80394F00)
        word = struct.unpack('>I', self.dol.read_at(ARENA_SETTER_VADDR + 4, 4))[0]
        self.assertEqual(word >> 26, 24)


class TestInjectAboveArena(unittest.TestCase):

    ARENA_LO = 0x80394E00  # 32-byte aligned

    def setUp(self):
        self.dol = build_mock_dol_with_arena(self.ARENA_LO)

    def test_single_section_placed_at_arena_lo(self):
        _, addrs = self.dol.inject_above_arena([b'\x60\x00\x00\x00' * 5])
        self.assertEqual(addrs[0], self.ARENA_LO + 0x100)

    def test_section_content_is_readable(self):
        code = b'\x38\x60\x00\x2a' * 4
        _, addrs = self.dol.inject_above_arena([code])
        self.assertEqual(self.dol.read_at(addrs[0], len(code)), code)

    def test_new_arena_is_32_byte_aligned(self):
        _, _ = self.dol.inject_above_arena([b'\x60\x00\x00\x00' * 5])  # 20 bytes
        new_lo = self.dol.read_arena_lo(ARENA_SETTER_VADDR)
        self.assertEqual(new_lo & 0x1F, 0)

    def test_new_arena_is_above_injected_code(self):
        code = b'\x60\x00\x00\x00' * 5
        _, addrs = self.dol.inject_above_arena([code])
        new_lo = self.dol.read_arena_lo(ARENA_SETTER_VADDR)
        self.assertGreater(new_lo, addrs[0] + len(code))

    def test_multiple_sections_placed_sequentially(self):
        code1 = b'\x60\x00\x00\x00' * 5
        code2 = b'\x38\x60\x00\x01' * 4
        _, addrs = self.dol.inject_above_arena([code1, code2])
        expected_addr2 = (addrs[0] + len(code1) + 31) & ~31
        self.assertEqual(addrs[1], expected_addr2)

    def test_multiple_sections_all_readable(self):
        code1 = b'\xAA\xBB\xCC\xDD' * 4
        code2 = b'\x11\x22\x33\x44' * 4
        _, addrs = self.dol.inject_above_arena([code1, code2])
        self.assertEqual(self.dol.read_at(addrs[0], len(code1)), code1)
        self.assertEqual(self.dol.read_at(addrs[1], len(code2)), code2)

    def test_reserved_size_fixes_arena(self):
        self.dol.inject_above_arena([b'\x60\x00\x00\x00' * 5], reserved_size=0x1000)
        new_lo = self.dol.read_arena_lo(ARENA_SETTER_VADDR)
        self.assertEqual(new_lo, self.ARENA_LO + 0x1100)

    def test_reserved_size_raises_when_code_too_large(self):
        code = b'\x60\x00\x00\x00' * 16  # 64 bytes
        with self.assertRaises(ValueError):
            self.dol.inject_above_arena([code], reserved_size=0x20)

    def test_multiple_difference_empiric_smg(self):
        code = b'\x60\x00\x00\x00' * 1294
        diff, _ = self.dol.inject_above_arena([code])
        self.assertEqual(diff, 0x1540)

        self.setUp()
        code = b'\x60\x00\x00\x00' * 201
        diff, _ = self.dol.inject_above_arena([code])
        self.assertEqual(diff, 0x440)

        self.setUp()
        code = b'\x60\x00\x00\x00' * 4630
        diff, _ = self.dol.inject_above_arena([code])
        self.assertEqual(diff, 0x4960)

        self.setUp()
        code = b'\x60\x00\x00\x00' * 4688
        diff, _ = self.dol.inject_above_arena([code])
        self.assertEqual(diff, 0x4a40)

        self.setUp()
        code = b'\x60\x00\x00\x00' * 506
        diff, _ = self.dol.inject_above_arena([code])
        self.assertEqual(diff, 0x900)

        self.setUp()
        code = b'\x60\x00\x00\x00' * 2597
        diff, _ = self.dol.inject_above_arena([code])
        self.assertEqual(diff, 0x29a0)

        self.setUp()
        code = b'\x60\x00\x00\x00' * 3181
        diff, _ = self.dol.inject_above_arena([code])
        self.assertEqual(diff, 0x32c0)

        self.setUp()
        code = b'\x60\x00\x00\x00' * 1574
        diff, _ = self.dol.inject_above_arena([code])
        self.assertEqual(diff, 0x19a0)

        self.setUp()
        code = b'\x60\x00\x00\x00' * 1632
        diff, _ = self.dol.inject_above_arena([code])
        self.assertEqual(diff, 0x1a80)

        self.setUp()
        code = b'\x60\x00\x00\x00' * 2551
        diff, _ = self.dol.inject_above_arena([code])
        self.assertEqual(diff, 0x28e0)

        self.setUp()
        code = b'\x60\x00\x00\x00' * 312
        diff, _ = self.dol.inject_above_arena([code])
        self.assertEqual(diff, 0x5e0)

        self.setUp()
        code = b'\x60\x00\x00\x00' * 577
        diff, _ = self.dol.inject_above_arena([code])
        self.assertEqual(diff, 0xa20)

        self.setUp()
        code = b'\x60\x00\x00\x00' * 1689
        diff, _ = self.dol.inject_above_arena([code])
        self.assertEqual(diff, 0x1b80)

        self.setUp()
        code = b'\x60\x00\x00\x00' * 3611
        diff, _ = self.dol.inject_above_arena([code])
        self.assertEqual(diff, 0x3980)

        self.setUp()
        code = b'\x60\x00\x00\x00' * 2981
        diff, _ = self.dol.inject_above_arena([code])
        self.assertEqual(diff, 0x2fa0)

        self.setUp()
        code = b'\x60\x00\x00\x00' * 741
        diff, _ = self.dol.inject_above_arena([code])
        self.assertEqual(diff, 0xca0)

if __name__ == '__main__':
    unittest.main()
