import unittest
import struct

from helpers.PowerPC import (
    b, bl, ba, bla,
    cntlzw,
    li, lis, addi, addis,
    lwz, stw, lbz, stb, lhz, sth,
    ori, nop,
    add, subf,
    or_, mr,
    mflr, mtlr, mfctr, mtctr,
    mfspr, mtspr, lfs, mulli, oris, rlwnm, stfs, andi, and_, blr,
)


def u32(data: bytes) -> int:
    return struct.unpack('>I', data)[0]

class TestGhidra(unittest.TestCase):

    def test_add(self):
        self.assertEqual(u32(add(3, 0, 27)), 0x7c60da14)  # Location: 0x 80180e0c - Instruction: 0x7c60da14 - Code:      add        r3,r0,r27
        self.assertEqual(u32(add(3, 31, 0)), 0x7c7f0214)  # Location: 0x 80180e98 - Instruction: 0x7c7f0214 - Code:      add        r3,r31,r0
        self.assertEqual(u32(add(3, 8, 0)), 0x7c680214)   # Location: 0x 80180eac - Instruction: 0x7c680214 - Code:      add        r3,r8,r0

    def test_addi(self):
        self.assertEqual(u32(addi(0, 3, 1)), 0x38030001)      # Location: 0x 80180e84 - Instruction: 0x38030001 - Code:      addi       r0,r3,0x1
        self.assertEqual(u32(addi(11, 1, 0xa0)), 0x396100a0)  # Location: 0x 80180f38 - Instruction: 0x396100a0 - Code:      addi       r11,r1,0xa0
        self.assertEqual(u32(addi(3, 1, 0x38)), 0x38610038)   # Location: 0x 80181078 - Instruction: 0x38610038 - Code:      addi       r3,r1,0x38
        self.assertEqual(u32(addi(0, 4, -0x1)), 0x3804ffff)   # Location: 0x 801810e8 - Instruction: 0x3804ffff - Code:      subi       r0,r4,0x1

    def test_and(self):
        self.assertEqual(u32(and_(3, 3, 0)), 0x7c630038) # Location: 0x8046e1ec - Instruction: 0x7c630038 - Code:     and        r3,r3,r0
        self.assertEqual(u32(and_(30, 4, 0)), 0x7c9e0038) # Location: 0x80473a38 - Instruction: 0x7c9e0038 - Code:     and        r30,r4,r0
        self.assertEqual(u32(and_(8, 0, 3)), 0x7c081838) # Location: 0x8047b84c - Instruction: 0x7c081838 - Code:     and        r8,r0,r3

    def test_andi(self):
        self.assertEqual(u32(andi(0, 30, 0x405)), 0x73c00405) # Location: 0x804af264 - Instruction: 0x73c00405 - Code:     andi.      r0,r30,0x405
        self.assertEqual(u32(andi(3, 3, 7)), 0x70630007) # Location: 0x804719a4 - Instruction: 0x70630007 - Code:     andi.      r3,r3,0x7
        self.assertEqual(u32(andi(0, 0, 0x405)), 0x70000405) # Location: 0x8052ce28 - Instruction: 0x70000405 - Code:     andi.      r0,r0,0x405

    def test_b(self):
        self.assertEqual(u32(b(0x804ae524, 0x800041a4)), 0x484aa380)  # Location: 0x 800041a4 - Instruction: 0x484aa380 - Code:      b          exit    (804ae524)                                         void exit(int __status)
        self.assertEqual(u32(b(0x800070f4, 0x800070c8)), 0x4800002c)  # Location: 0x 800070c8 - Instruction: 0x4800002c - Code:      b          LAB_800070f4
        self.assertEqual(u32(b(0x800072ac, 0x80007284)), 0x48000028)  # Location: 0x 80007284 - Instruction: 0x48000028 - Code:      b          LAB_800072ac

    def test_bl(self):
        self.assertEqual(u32(bl(0x80517530, 0x800074ec)), 0x48510045)  # Location: 0x 800074ec - Instruction: 0x48510045 - Code:      bl         FUN_80517530
        self.assertEqual(u32(bl(0x80009ea8, 0x80007758)), 0x48002751)  # Location: 0x 80007758 - Instruction: 0x48002751 - Code:      bl         FUN_80009ea8
        self.assertEqual(u32(bl(0x80409b40, 0x8000849c)), 0x484016a5)  # Location: 0x 8000849c - Instruction: 0x484016a5 - Code:      bl         __dl__FPv  (0x80409b40)

    def test_bc(self):
        self.assertEqual(u32(nop()), 0x60000000)
        self.assertEqual(u32(nop()), 0x60000000)
        self.assertEqual(u32(nop()), 0x60000000)

    def test_bcl(self):
        self.assertEqual(u32(nop()), 0x60000000)
        self.assertEqual(u32(nop()), 0x60000000)
        self.assertEqual(u32(nop()), 0x60000000)

    def test_cmp(self):
        self.assertEqual(u32(nop()), 0x60000000)
        self.assertEqual(u32(nop()), 0x60000000)
        self.assertEqual(u32(nop()), 0x60000000)

    def test_cmpi(self):
        self.assertEqual(u32(nop()), 0x60000000)
        self.assertEqual(u32(nop()), 0x60000000)
        self.assertEqual(u32(nop()), 0x60000000)

    def test_cntlzw(self):
        self.assertEqual(u32(cntlzw(0, 28)), 0x7f800034)  # Location: 0x8000aa50  - Instruction: 0x7f800034 - Code: cntlzw     r0, r28
        self.assertEqual(u32(cntlzw(0, 3)), 0x7c600034)   # Location: 0x801ba4d8  - Instruction: 0x7c600034 - Code: cntlzw     r0, r3
        self.assertEqual(u32(cntlzw(0, 29)), 0x7fa00034)  # Location: 0x80318c54  - Instruction: 0x7fa00034 - Code: cntlzw     r0, r29


    def test_lbz(self):
        self.assertEqual(u32(lbz(5, 1, 7)), 0x88a70001)         # Location: 0x8000726c  - Instruction: 0x88a70001 - Code: lbz        r5, 0x1 (r7)
        self.assertEqual(u32(lbz(0, 0x43, 31)), 0x881f0043)     # Location: 0x800075b4  - Instruction: 0x881f0043 - Code: lbz        r0, 0x43 (r31 )
        self.assertEqual(u32(lbz(6, -0x67fb, 13)), 0x88cd9805)  # Location: 0x800089d0  - Instruction: 0x88cd9805 - Code: lbz        r6, -0x67fb (r13 )=>DAT_8069e4a4+1


    def test_lhz(self):
        self.assertEqual(u32(lhz(4, 0x10, 31)), 0xa09f0010)   # Location: 0x8000b870  - Instruction: 0xa09f0010 - Code: lhz        r4, 0x10 (r31 )
        self.assertEqual(u32(lhz(0, 0x1C, 28)), 0xa01c001c)   # Location: 0x80014c08  - Instruction: 0xa01c001c - Code: lhz        r0, 0x1c (r28 )
        self.assertEqual(u32(lhz(4, 0x22C, 25)), 0xa099022c)  # Location: 0x80033528  - Instruction: 0xa099022c - Code: lhz        r4, 0x22c (r25 )

    def test_lwz(self):
        self.assertEqual(u32(lwz(30, 0x58, 31)), 0x83df0058)  # Location: 0x8000740c  - Instruction: 0x83df0058 - Code:     lwz        r30 ,0x58 (r31 )
        self.assertEqual(u32(lwz(3, 0x8, 3)), 0x80630008)     # Location: 0x80007c34  - Instruction: 0x80630008 - Code:     lwz        r3,0x8 (r3)
        self.assertEqual(u32(lwz(0, 0x1c, 4)), 0x8004001c)    # Location: 0x80008404  - Instruction: 0x8004001c - Code:     lwz        r0,0x1c (r4)

    def test_lfs(self):
        self.assertEqual(u32(lfs(31, 0x8, 6)), 0xc3e60008)    # Location: 0x80007528  - Instruction: 0xc3e60008 - Code: lfs        f31, 0x8 (r6)
        self.assertEqual(u32(lfs(30, 0x30, 31)), 0xc3df0030)  # Location    : 0x8000752c  - Instruction: 0xc3df0030 - Code: lfs        f30, 0x30 (r31 )
        self.assertEqual(u32(lfs(1, 0x44, 31)), 0xc03f0044)   # Location : 0x800075c0  - Instruction: 0xc03f0044 - Code: lfs        f1, 0x44 (r31 )

    def test_li(self):
        self.assertEqual(u32(li(26, 0x0)), 0x3b400000)       # Location: 0x80004204  - Instruction: 0x3b400000 - Code: li         r26, 0x0
        self.assertEqual(u32(li(0,      -0x1)), 0x3800ffff)  # Location: 0x80004044  - Instruction: 0x3800ffff - Code: li         r0, -0x1
        self.assertEqual(u32(li(5, 0x2)), 0x38a00002)        # Location: 0x800040c4  - Instruction: 0x38a00002 - Code: li         r5, 0x2

    def test_lis(self):
        self.assertEqual(u32(lis(6, -0x8000)), 0x3cc08000)  # Location: 0x8000405c  - Instruction: 0x3cc08000 - Code:     liss        r6,-0x8000
        self.assertEqual(u32(lis(6, -0x7fad)), 0x3cc08053)  # Location: 0x800040d0  - Instruction: 0x3cc08053 - Code:     lis        r6,-0x7fad
        self.assertEqual(u32(lis(4, 0x5246)), 0x3c805246)   # Location: 0x80008464  - Instruction: 0x3c805246 - Code:     lis        r4,0x5246

    def test_mulli(self):
        self.assertEqual(u32(mulli(0, 31, 0xa)), 0x1c1f000a)    # Location: 0x8000fee0  - Instruction: 0x1c1f000a - Code:     mulli      r0,r31 ,0xa
        self.assertEqual(u32(mulli(4, 3, 0x14)), 0x1c830014)    # Location: 0x800129d4  - Instruction: 0x1c830014 - Code:     mulli      r4,r3,0x14
        self.assertEqual(u32(mulli(24, 31, 0x70)), 0x1f1f0070)  # Location: 0x80019e2c  - Instruction: 0x1f1f0070 - Code:     mulli      r24 ,r31 ,0x70

    def test_or(self):
        self.assertEqual(u32(or_(5, 30, 30)), 0x7fc5f378)  # Location: 0x8000427c  - Instruction: 0x7fc5f378 - Code:     or         r5,r30 ,r30
        self.assertEqual(u32(or_(3, 5, 5)), 0x7ca32b78)    # Location: 0x80007164  - Instruction: 0x7ca32b78 - Code:     or         r3,r5,r5
        self.assertEqual(u32(or_(6, 7, 7)), 0x7ce63b78)    # Location: 0x80007158  - Instruction: 0x7ce63b78 - Code:     or         r6,r7,r7

    def test_ori(self):
        self.assertEqual(u32(ori(3, 3, 0x30)), 0x60630030)    # Location: 0x800046f0  - Instruction: 0x60630030 - Code:     ori        r3,r3,0x30
        self.assertEqual(u32(ori(3, 3, 0x9aa0)), 0x60639aa0)  # Location: 0x800046fc  - Instruction: 0x60639aa0 - Code:     ori        r3,r3,0x9aa0

    def test_oris(self):
        self.assertEqual(u32(oris(3, 3, 0x5)),0x64630005)  # Location: 0x8000bd1c  - Instruction: 0x64630005 - Code:     oris       r3,r3,0x5

    def test_nop(self):
        self.assertEqual(u32(nop()), 0x60000000)

    def test_rlwnm(self):
        self.assertEqual(u32(rlwnm(3,3,0,0x1f ,0x1f)), 0x5c6307fe)      # Location: 0x80070c60  - Instruction: 0x5c6307fe - Code:     rlwnm      r3,r3,r0,0x1f ,0x1f
        self.assertEqual(u32(rlwnm(10 ,11 ,9,0x1f ,0x1f)), 0x5d6a4ffe)  # Location: 0x8045371c  - Instruction: 0x5d6a4ffe - Code:     rlwnm      r10 ,r11 ,r9,0x1f ,0x1f

    def test_stb(self):
        self.assertEqual(u32(stb(6, 5, 4)), 0x98c40005)      # Location: 0x8000812c  - Instruction: 0x98c40005 - Code:     stb        r6,0x5 (r4)
        self.assertEqual(u32(stb(3, 0x10, 31)), 0x987f0010)  # Location: 0x800085ac  - Instruction: 0x987f0010 - Code:     stb        r3,0x10 (r31)
        self.assertEqual(u32(stb(5, 0x1a, 3)), 0x98a3001a)   # Location: 0x8000873c  - Instruction: 0x98a3001a - Code:     stb        r5,0x1a (r3)

    def test_sth(self):
        self.assertEqual(u32(sth(0, 0x12, 4)), 0xb0040012)      # Location: 0x8000815c  - Instruction: 0xb0040012 - Code:     sth        r0,0x12 (r4)
        self.assertEqual(u32(sth(31, -0x8000, 3)), 0xb3e38000)        # Location: 0x80009808  - Instruction: 0xb3e38000 - Code:     sth        r31 ,-0x8000 (r3)=>DAT_cc008000                   = ??
        self.assertEqual(u32(sth(31, 0xf8, 30)), 0xb3fe00f8)    # Location: 0x8000e884  - Instruction: 0xb3fe00f8 - Code:     sth        r31 ,0xf8 (r30 )

    def test_stw(self):
        self.assertEqual(u32(stw(7, 0x18, 3)), 0x90e30018)  # Location: 0x800043f8  - Instruction: 0x90e30018 - Code:     stw        r7,0x18 (r3)
        self.assertEqual(u32(stw(8, 0x18, 3)), 0x91030018)  # Location: 0x80008508  - Instruction: 0x91030018 - Code:     stw        r8,0x18 (r3)
        self.assertEqual(u32(stw(7, 0, 6)), 0x90e60000)     # Location: 0x80004124  - Instruction: 0x90e60000 - Code:     stw        r7,0x0 (r6)

    def test_stfs(self):
        self.assertEqual(u32(stfs(0, 0, 27)), 0xd01b0000)        # Location: 0x80007548  - Instruction: 0xd01b0000 - Code:     stfs       f0,0x0 (r27 )
        self.assertEqual(u32(stfs(0, 0x2c, 31)), 0xd01f002c)     # Location: 0x80007994  - Instruction: 0xd01f002c - Code:     stfs       f0,0x2c (r31 )
        self.assertEqual(u32(stfs(29, -0x8000, 3)), 0xd3a38000)        # Location: 0x80009850  - Instruction: 0xd3a38000 - Code:     stfs       f29 ,-0x8000 (r3)=>DAT_cc008000                   = ??

    def test_blr(self):
        self.assertEqual(u32(blr()), 0x4e800020)

    def test_function_unstack(self):
        byte_result = b''
        byte_result += or_(3, 31, 31)
        byte_result += lwz(31, 0x1C, 1)
        byte_result += lwz(30, 0x18, 1)
        byte_result += lwz(29, 0x14, 1)
        byte_result += lwz(28, 0x10, 1)
        byte_result += lwz(0, 0x24, 1)
        byte_result += mtspr(8, 0)
        byte_result += addi(1, 1, 0x20)
        byte_result += blr()

        self.assertEqual(byte_result, b'\x7f\xe3\xfb\x78\x83\xe1\x00\x1c\x83\xc1\x00\x18\x83\xa1\x00\x14\x83\x81\x00\x10\x80\x01\x00\x24\x7c\x08\x03\xa6\x38\x21\x00\x20\x4e\x80\x00\x20')

    def test_big_giant_function(self):
        byte_result = b''


if __name__ == '__main__':
    unittest.main()
