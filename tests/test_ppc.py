import unittest
import struct

from helpers.PowerPC import (
    b, bl, ba, bla,
    li, lis, addi, addis,
    lwz, stw, lbz, stb, lhz, sth,
    ori, nop,
    add, subf,
    or_, mr,
    mflr, mtlr, mfctr, mtctr,
    mfspr, mtspr,
)


def u32(data: bytes) -> int:
    return struct.unpack('>I', data)[0]

class TestGhidra(unittest.TestCase):

    def test_add(self):
        self.assertEqual(u32(add(3, 0, 27)), 0x7c60da14) # 80180e0c 7c 60 da 14     add        r3,r0,r27
        self.assertEqual(u32(add(3, 31, 0)), 0x7c7f0214) # 80180e98 7c 7f 02 14     add        r3,r31,r0
        self.assertEqual(u32(add(3, 8, 0)), 0x7c680214)  # 80180eac 7c 68 02 14     add        r3,r8,r0

    def test_addi(self):
        self.assertEqual(u32(addi(0, 3, 1)), 0x38030001)     # 80180e84 38 03 00 01     addi       r0,r3,0x1
        self.assertEqual(u32(addi(11, 1, 0xa0)), 0x396100a0) # 80180f38 39 61 00 a0     addi       r11,r1,0xa0
        self.assertEqual(u32(addi(3, 1, 0x38)), 0x38610038)  # 80181078 38 61 00 38     addi       r3,r1,0x38
        self.assertEqual(u32(addi(0, 4, -0x1)), 0x3804ffff)       # 801810e8 38 04 ff ff     subi       r0,r4,0x1

    def test_and(self):
        ...

    def test_andi(self):
        ...

    def test_b(self):
        self.assertEqual(u32(b(0x804ae524, 0x800041a4)), 0x484aa380) # 800041a4 48 4a a3 80     b          exit    (804ae524)                                         void exit(int __status)
        self.assertEqual(u32(b(0x800070f4, 0x800070c8)), 0x4800002c) # 800070c8 48 00 00 2c     b          LAB_800070f4
        self.assertEqual(u32(b(0x800072ac, 0x80007284)), 0x48000028) # 80007284 48 00 00 28     b          LAB_800072ac

    def test_bl(self):
        self.assertEqual(u32(bl(0x80517530, 0x800074ec)), 0x48510045) # 800074ec 48 51 00 45     bl         FUN_80517530
        self.assertEqual(u32(bl(0x80009ea8, 0x80007758)), 0x48002751) # 80007758 48 00 27 51     bl         FUN_80009ea8
        self.assertEqual(u32(bl(0x80409b40, 0x8000849c)), 0x484016a5) # 8000849c 48 40 16 a5     bl         __dl__FPv  (0x80409b40)

    def test_bc(self):
        ...

    def test_bcl(self):
        ...

    def test_cmp(self):
        ...

    def test_cmpi(self):
        ...

    def test_cntlzw(self):
        ...
        # 8000aa50 7f  80  00  34    cntlzw     r0,r28
        # 801ba4d8 7c  60  00  34    cntlzw     r0,r3
        # 80318c54 7f  a0  00  34    cntlzw     r0,r29

    def test_lbz(self):
        ...

    def test_lhz(self):
        ...

    def test_lwz(self):
        ...

    def test_lfs(self):
        ...

    def test_li(self):
        ...

    def test_lis(self):
        ...

    def test_mulli(self):
        ...

    def test_or(self):
        ...

    def test_ori(self):
        ...

    def test_nop(self):
        ...

    def test_rlwnm(self):
        ...

    def test_stb(self):
        ...

    def test_sth(self):
        ...

    def test_stw(self):
        ...

    def test_stfs(self):
        ...



if __name__ == '__main__':
    unittest.main()
