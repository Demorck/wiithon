import math
import unittest
from io import BytesIO

from wiithon.binary.reader import BinaryReader
from wiithon.exceptions import BinaryError


def reader(data: bytes, **kwargs) -> BinaryReader:
    return BinaryReader(BytesIO(data), **kwargs)


class TestUnsignedNumbers(unittest.TestCase):
    def test_u8(self):
        self.assertEqual(reader(b"\x00").u8(), 0)
        self.assertEqual(reader(b"\x7F").u8(), 127)
        self.assertEqual(reader(b"\xFF").u8(), 255)

    def test_u16_is_big_endian(self):
        self.assertEqual(reader(b"\x00\x00").u16(), 0)
        self.assertEqual(reader(b"\x01\x02").u16(), 0x0102)
        self.assertEqual(reader(b"\xFF\xFF").u16(), 65535)

    def test_u32_is_big_endian(self):
        self.assertEqual(reader(b"\x01\x02\x03\x04").u32(), 0x01020304)
        self.assertEqual(reader(b"\xFF\xFF\xFF\xFF").u32(), 0xFFFFFFFF)

    def test_u64_is_big_endian(self):
        self.assertEqual(reader(b"\x01\x02\x03\x04\x05\x06\x07\x08").u64(), 0x0102030405060708)
        self.assertEqual(reader(b"\xFF" * 8).u64(), 0xFFFFFFFFFFFFFFFF)


class TestSignedNumbers(unittest.TestCase):
    def test_s8(self):
        self.assertEqual(reader(b"\x00").s8(), 0)
        self.assertEqual(reader(b"\x7F").s8(), 127)
        self.assertEqual(reader(b"\x80").s8(), -128)
        self.assertEqual(reader(b"\xFF").s8(), -1)

    def test_s16(self):
        self.assertEqual(reader(b"\x7F\xFF").s16(), 32767)
        self.assertEqual(reader(b"\x80\x00").s16(), -32768)
        self.assertEqual(reader(b"\xFF\xFF").s16(), -1)

    def test_s32(self):
        self.assertEqual(reader(b"\x7F\xFF\xFF\xFF").s32(), 2147483647)
        self.assertEqual(reader(b"\x80\x00\x00\x00").s32(), -2147483648)
        self.assertEqual(reader(b"\xFF\xFF\xFF\xFF").s32(), -1)

    def test_s64(self):
        self.assertEqual(reader(b"\x7F" + b"\xFF" * 7).s64(), 2**63 - 1)
        self.assertEqual(reader(b"\x80" + b"\x00" * 7).s64(), -(2**63))
        self.assertEqual(reader(b"\xFF" * 8).s64(), -1)

    def test_signed_and_unsigned_read_the_same_bytes(self):
        self.assertEqual(reader(b"\xFF\xFF\xFF\xFF").u32(), 0xFFFFFFFF)
        self.assertEqual(reader(b"\xFF\xFF\xFF\xFF").s32(), -1)


class TestFloat(unittest.TestCase):
    def test_known_values(self):
        self.assertEqual(reader(b"\x00\x00\x00\x00").float(), 0.0)
        self.assertEqual(reader(b"\x3F\x80\x00\x00").float(), 1.0)
        self.assertEqual(reader(b"\x3F\xC0\x00\x00").float(), 1.5)
        self.assertEqual(reader(b"\xBF\x00\x00\x00").float(), -0.5)
        self.assertEqual(reader(b"\xC7\x00\x00\x00").float(), -32768.0)

    def test_negative_zero(self):
        value = reader(b"\x80\x00\x00\x00").float()
        self.assertEqual(value, 0.0)
        self.assertEqual(math.copysign(1, value), -1.0)

    def test_infinity(self):
        self.assertEqual(reader(b"\x7F\x80\x00\x00").float(), math.inf)
        self.assertEqual(reader(b"\xFF\x80\x00\x00").float(), -math.inf)

    def test_nan(self):
        self.assertTrue(math.isnan(reader(b"\x7F\xC0\x00\x00").float()))


class TestEndianVariants(unittest.TestCase):
    def test_u32_le_reads_the_other_way_round(self):
        self.assertEqual(reader(b"\x01\x02\x03\x04").u32_le(), 0x04030201)

    def test_u32_and_u32_le_on_the_same_bytes(self):
        data = b"\x00\x00\x00\x01"
        self.assertEqual(reader(data).u32(), 1)
        self.assertEqual(reader(data).u32_le(), 0x01000000)

    def test_u32_shifted_multiplies_by_four(self):
        self.assertEqual(reader(b"\x00\x00\x00\x01").u32_shifted(), 4)
        self.assertEqual(reader(b"\x00\x00\x20\x00").u32_shifted(), 0x8000)
        self.assertEqual(reader(b"\x00\x00\x00\x00").u32_shifted(), 0)


class TestPositioning(unittest.TestCase):
    def test_reads_advance_the_position(self):
        binary_reader = reader(b"\x01\x02\x03\x04\x05\x06\x07")
        self.assertEqual(binary_reader.tell(), 0)
        binary_reader.u8()
        self.assertEqual(binary_reader.tell(), 1)
        binary_reader.u16()
        self.assertEqual(binary_reader.tell(), 3)
        binary_reader.u32()
        self.assertEqual(binary_reader.tell(), 7)

    def test_seek(self):
        binary_reader = reader(b"\x00\x01\x02\x03")
        binary_reader.seek(2)
        self.assertEqual(binary_reader.tell(), 2)
        self.assertEqual(binary_reader.u8(), 2)

    def test_seek_backwards_allows_rereading(self):
        binary_reader = reader(b"\xAA\xBB")
        self.assertEqual(binary_reader.u8(), 0xAA)
        binary_reader.seek(0)
        self.assertEqual(binary_reader.u8(), 0xAA)

    def test_skip(self):
        binary_reader = reader(b"\x01\x02\x03\x04")
        binary_reader.skip(3)
        self.assertEqual(binary_reader.tell(), 3)
        self.assertEqual(binary_reader.u8(), 4)

    def test_skip_zero_is_a_no_op(self):
        binary_reader = reader(b"\x01")
        binary_reader.skip(0)
        self.assertEqual(binary_reader.tell(), 0)

    def test_skip_past_the_end_stops_at_the_end(self):
        binary_reader = reader(b"\x01\x02")
        binary_reader.skip(100)
        self.assertEqual(binary_reader.tell(), 2)

    def test_seek_past_the_end_then_read_fails(self):
        binary_reader = reader(b"\x01\x02")
        binary_reader.seek(10)
        with self.assertRaises(BinaryError):
            binary_reader.u8()


class TestBytes(unittest.TestCase):
    def test_exact_size(self):
        self.assertEqual(reader(b"\x01\x02\x03").raw(2), b"\x01\x02")

    def test_zero_size(self):
        binary_reader = reader(b"\x01\x02")
        self.assertEqual(binary_reader.raw(0), b"")
        self.assertEqual(binary_reader.tell(), 0)

    def test_default_reads_until_the_end(self):
        binary_reader = reader(b"\x01\x02\x03")
        binary_reader.skip(1)
        self.assertEqual(binary_reader.raw(), b"\x02\x03")

    def test_default_at_the_end_returns_empty(self):
        binary_reader = reader(b"\x01")
        binary_reader.skip(1)
        self.assertEqual(binary_reader.raw(), b"")

    def test_reading_more_than_available_fails(self):
        with self.assertRaises(BinaryError):
            reader(b"\x01\x02").raw(3)


class TestListU32(unittest.TestCase):
    def test_reads_consecutive_values(self):
        data = b"\x00\x00\x00\x01" b"\x00\x00\x00\x02" b"\x00\x00\x00\x03"
        self.assertEqual(reader(data).list_u32(3), [1, 2, 3])

    def test_zero_length(self):
        binary_reader = reader(b"\x00\x00\x00\x01")
        self.assertEqual(binary_reader.list_u32(0), [])
        self.assertEqual(binary_reader.tell(), 0)

    def test_stops_at_the_requested_count(self):
        data = b"\x00\x00\x00\x01" b"\x00\x00\x00\x02"
        binary_reader = reader(data)
        self.assertEqual(binary_reader.list_u32(1), [1])
        self.assertEqual(binary_reader.tell(), 4)

    def test_truncated_list(self):
        with self.assertRaises(BinaryError):
            reader(b"\x00\x00\x00\x01\x00\x00").list_u32(2)


class TestString(unittest.TestCase):
    def test_stops_at_the_first_null(self):
        self.assertEqual(reader(b"name\x00\x00\x00\x00").string(8), "name")

    def test_consumes_the_full_size_even_when_null_terminated(self):
        binary_reader = reader(b"ab\x00\x00\x01")
        self.assertEqual(binary_reader.string(4), "ab")
        self.assertEqual(binary_reader.tell(), 4)

    def test_field_without_a_terminator(self):
        self.assertEqual(reader(b"abcd").string(4), "abcd")

    def test_empty_field(self):
        self.assertEqual(reader(b"\x00\x00").string(2), "")

    def test_zero_size(self):
        self.assertEqual(reader(b"abc").string(0), "")

    def test_junk_after_the_null_is_ignored(self):
        self.assertEqual(reader(b"ok\x00\xFF\xFF\xFF").string(6), "ok")

    def test_default_encoding_is_utf8(self):
        self.assertEqual(reader("héllo".encode()).string(6), "héllo")

    def test_encoding_from_the_constructor(self):
        binary_reader = reader(b"caf\xE9", encoding="latin-1")
        self.assertEqual(binary_reader.string(4), "café")

    def test_encoding_override_per_call(self):
        binary_reader = reader(b"caf\xE9")
        self.assertEqual(binary_reader.string(4, encoding="latin-1"), "café")

    def test_shift_jis(self):
        data = "テスト".encode("shift_jis")
        self.assertEqual(reader(data, encoding="shift_jis").string(len(data)), "テスト")

    def test_invalid_encoding_raises(self):
        with self.assertRaises(UnicodeDecodeError):
            reader(b"\xFF\xFE").string(2)

    def test_reading_past_the_end_fails(self):
        with self.assertRaises(BinaryError):
            reader(b"ab").string(4)


class TestStringUntilNull(unittest.TestCase):
    def test_reads_up_to_the_terminator(self):
        self.assertEqual(reader(b"hello\x00world\x00").string_until_null(), "hello")

    def test_consumes_the_terminator(self):
        binary_reader = reader(b"hello\x00world\x00")
        self.assertEqual(binary_reader.string_until_null(), "hello")
        self.assertEqual(binary_reader.tell(), 6)
        self.assertEqual(binary_reader.string_until_null(), "world")

    def test_empty_string(self):
        binary_reader = reader(b"\x00rest")
        self.assertEqual(binary_reader.string_until_null(), "")
        self.assertEqual(binary_reader.tell(), 1)

    def test_unterminated_string_stops_at_the_end(self):
        self.assertEqual(reader(b"tail").string_until_null(), "tail")

    def test_at_the_end_of_the_stream(self):
        binary_reader = reader(b"")
        self.assertEqual(binary_reader.string_until_null(), "")

    def test_from_an_arbitrary_offset(self):
        binary_reader = reader(b"hello\x00world\x00")
        binary_reader.seek(6)
        self.assertEqual(binary_reader.string_until_null(), "world")

    def test_multibyte_utf8(self):
        self.assertEqual(reader("héllo".encode() + b"\x00").string_until_null(), "héllo")

    def test_encoding_override_per_call(self):
        self.assertEqual(reader(b"caf\xE9\x00").string_until_null(encoding="latin-1"), "café")


class TestTruncatedReads(unittest.TestCase):
    def test_every_numeric_type_needs_its_full_width(self):
        cases = [
            ("u8", 1), ("u16", 2), ("u32", 4), ("u64", 8),
            ("s8", 1), ("s16", 2), ("s32", 4), ("s64", 8),
            ("float", 4), ("u32_le", 4), ("u32_shifted", 4),
        ]
        for method, size in cases:
            with self.subTest(method=method):
                binary_reader = reader(b"\x00" * (size - 1))
                with self.assertRaises(BinaryError):
                    getattr(binary_reader, method)()

    def test_error_mentions_the_offset_of_the_failed_read(self):
        binary_reader = reader(b"\x00\x00\x00\x00\x01\x02")
        binary_reader.u32()
        with self.assertRaises(BinaryError) as context:
            binary_reader.u32()
        self.assertIn("offset 4", str(context.exception))

    def test_reading_at_the_end_of_the_stream(self):
        binary_reader = reader(b"\x01")
        binary_reader.u8()
        with self.assertRaises(BinaryError):
            binary_reader.u8()


class TestSequentialRead(unittest.TestCase):
    def test_mixed_hand_written_record(self):
        raw = (
            b"\x01"                          # u8  = 1
            b"\xFF\xFE"                      # s16 = -2
            b"\x00\x00\x01\x00"              # u32 = 256
            b"\x3F\x80\x00\x00"              # float = 1.0
            b"name\x00\x00"                  # string(6) = "name"
            b"\x00\x00\x00\x02"              # u32 = 2
            b"\x00\x00\x00\x0A\x00\x00\x00\x0B"  # list_u32(2) = [10, 11]
        )
        binary_reader = reader(raw)

        self.assertEqual(binary_reader.u8(), 1)
        self.assertEqual(binary_reader.s16(), -2)
        self.assertEqual(binary_reader.u32(), 256)
        self.assertEqual(binary_reader.float(), 1.0)
        self.assertEqual(binary_reader.string(6), "name")
        count = binary_reader.u32()
        self.assertEqual(binary_reader.list_u32(count), [10, 11])
        self.assertEqual(binary_reader.tell(), len(raw))
        self.assertEqual(binary_reader.raw(), b"")

    def test_two_readers_share_one_stream_position(self):
        stream = BytesIO(b"\x01\x02")
        first = BinaryReader(stream)
        second = BinaryReader(stream)

        self.assertEqual(first.u8(), 1)
        self.assertEqual(second.u8(), 2)


if __name__ == "__main__":
    unittest.main()