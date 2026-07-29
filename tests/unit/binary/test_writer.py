import math
import struct
import unittest
from io import BytesIO

from wiithon.binary.reader import BinaryReader
from wiithon.binary.writer import BinaryWriter
from wiithon.exceptions import BinaryError


def writer(**kwargs) -> tuple[BinaryWriter, BytesIO]:
    stream = BytesIO()
    return BinaryWriter(stream, **kwargs), stream


def written(method: str, *args, **kwargs) -> bytes:
    binary_writer, stream = writer()
    getattr(binary_writer, method)(*args, **kwargs)
    return stream.getvalue()


class TestUnsignedNumbers(unittest.TestCase):
    def test_u8(self):
        self.assertEqual(written("u8", 0), b"\x00")
        self.assertEqual(written("u8", 127), b"\x7F")
        self.assertEqual(written("u8", 255), b"\xFF")

    def test_u16_is_big_endian(self):
        self.assertEqual(written("u16", 0x0102), b"\x01\x02")
        self.assertEqual(written("u16", 65535), b"\xFF\xFF")

    def test_u32_is_big_endian(self):
        self.assertEqual(written("u32", 0x01020304), b"\x01\x02\x03\x04")
        self.assertEqual(written("u32", 0xFFFFFFFF), b"\xFF\xFF\xFF\xFF")

    def test_u64_is_big_endian(self):
        self.assertEqual(written("u64", 0x0102030405060708),
                         b"\x01\x02\x03\x04\x05\x06\x07\x08")


class TestSignedNumbers(unittest.TestCase):
    def test_s8(self):
        self.assertEqual(written("s8", 0), b"\x00")
        self.assertEqual(written("s8", 127), b"\x7F")
        self.assertEqual(written("s8", -1), b"\xFF")
        self.assertEqual(written("s8", -128), b"\x80")

    def test_s16(self):
        self.assertEqual(written("s16", 32767), b"\x7F\xFF")
        self.assertEqual(written("s16", -32768), b"\x80\x00")
        self.assertEqual(written("s16", -1), b"\xFF\xFF")

    def test_s32(self):
        self.assertEqual(written("s32", 2147483647), b"\x7F\xFF\xFF\xFF")
        self.assertEqual(written("s32", -2147483648), b"\x80\x00\x00\x00")
        self.assertEqual(written("s32", -1), b"\xFF\xFF\xFF\xFF")

    def test_s64(self):
        self.assertEqual(written("s64", -1), b"\xFF" * 8)
        self.assertEqual(written("s64", 2**63 - 1), b"\x7F" + b"\xFF" * 7)


class TestOutOfRangeValues(unittest.TestCase):
    """struct.error is what surfaces today; it is not wrapped in BinaryError."""

    def test_unsigned_overflow(self):
        cases = [("u8", 256), ("u8", -1), ("u16", 65536), ("u32", 1 << 32), ("u64", 1 << 64)]
        for method, value in cases:
            with self.subTest(method=method, value=value):
                with self.assertRaises(struct.error):
                    written(method, value)

    def test_signed_overflow(self):
        cases = [("s8", 128), ("s8", -129), ("s16", 32768), ("s32", 1 << 31), ("s64", 1 << 63)]
        for method, value in cases:
            with self.subTest(method=method, value=value):
                with self.assertRaises(struct.error):
                    written(method, value)

    def test_float_out_of_32_bit_range(self):
        # note: OverflowError here, struct.error for the integer types
        with self.assertRaises(OverflowError):
            written("float", 1e40)

    def test_non_integer_value(self):
        with self.assertRaises(struct.error):
            written("u32", 1.5)


class TestFloat(unittest.TestCase):
    def test_known_values(self):
        self.assertEqual(written("float", 0.0), b"\x00\x00\x00\x00")
        self.assertEqual(written("float", 1.0), b"\x3F\x80\x00\x00")
        self.assertEqual(written("float", 1.5), b"\x3F\xC0\x00\x00")
        self.assertEqual(written("float", -0.5), b"\xBF\x00\x00\x00")

    def test_negative_zero(self):
        self.assertEqual(written("float", -0.0), b"\x80\x00\x00\x00")

    def test_infinity(self):
        self.assertEqual(written("float", math.inf), b"\x7F\x80\x00\x00")
        self.assertEqual(written("float", -math.inf), b"\xFF\x80\x00\x00")

    def test_integers_are_accepted(self):
        self.assertEqual(written("float", 1), b"\x3F\x80\x00\x00")

    def test_precision_is_truncated_to_32_bit(self):
        stream = BytesIO(written("float", 0.1))
        self.assertNotEqual(BinaryReader(stream).float(), 0.1)


class TestEndianVariants(unittest.TestCase):
    def test_u32_le(self):
        self.assertEqual(written("u32_le", 0x01020304), b"\x04\x03\x02\x01")

    def test_u32_shifted_divides_by_four(self):
        self.assertEqual(written("u32_shifted", 4), b"\x00\x00\x00\x01")
        self.assertEqual(written("u32_shifted", 0x8000), b"\x00\x00\x20\x00")

    def test_u32_shifted_drops_the_low_two_bits(self):
        # values that are not 4-aligned cannot survive the roundtrip
        self.assertEqual(written("u32_shifted", 7), written("u32_shifted", 4))


class TestBytesAndPad(unittest.TestCase):
    def test_bytes(self):
        self.assertEqual(written("raw", b"\x01\x02\x03"), b"\x01\x02\x03")

    def test_empty_bytes(self):
        self.assertEqual(written("raw", b""), b"")

    def test_pad_defaults_to_null_bytes(self):
        self.assertEqual(written("pad", 4), b"\x00\x00\x00\x00")

    def test_pad_with_a_custom_byte(self):
        self.assertEqual(written("pad", 3, b"@"), b"@@@")

    def test_pad_zero_writes_nothing(self):
        self.assertEqual(written("pad", 0), b"")


class TestListU32(unittest.TestCase):
    def test_writes_consecutive_values(self):
        self.assertEqual(written("list_u32", [1, 2, 3]),
                         b"\x00\x00\x00\x01" b"\x00\x00\x00\x02" b"\x00\x00\x00\x03")

    def test_empty_list(self):
        self.assertEqual(written("list_u32", []), b"")

    def test_propagates_out_of_range_values(self):
        with self.assertRaises(struct.error):
            written("list_u32", [1, 1 << 32])


class TestPositioning(unittest.TestCase):
    def test_writes_advance_the_position(self):
        binary_writer, _ = writer()
        self.assertEqual(binary_writer.tell(), 0)
        binary_writer.u8(1)
        self.assertEqual(binary_writer.tell(), 1)
        binary_writer.u32(1)
        self.assertEqual(binary_writer.tell(), 5)

    def test_seek_then_overwrite(self):
        binary_writer, stream = writer()
        binary_writer.u32(0)
        binary_writer.seek(0)
        binary_writer.u32(0xDEADBEEF)

        self.assertEqual(stream.getvalue(), b"\xDE\xAD\xBE\xEF")

    def test_patch_in_the_middle(self):
        binary_writer, stream = writer()
        binary_writer.raw(b"\x00" * 8)
        binary_writer.seek(4)
        binary_writer.u16(0xABCD)

        self.assertEqual(stream.getvalue(), b"\x00\x00\x00\x00\xAB\xCD\x00\x00")

    def test_seek_past_the_end_zero_fills(self):
        binary_writer, stream = writer()
        binary_writer.seek(4)
        binary_writer.u8(0xFF)

        self.assertEqual(stream.getvalue(), b"\x00\x00\x00\x00\xFF")

    def test_size_of_an_empty_stream(self):
        binary_writer, _ = writer()
        self.assertEqual(binary_writer.size(), 0)

    def test_size_reports_the_whole_stream(self):
        binary_writer, _ = writer()
        binary_writer.raw(b"\x00" * 10)
        self.assertEqual(binary_writer.size(), 10)

    def test_size_does_not_move_the_position(self):
        binary_writer, _ = writer()
        binary_writer.raw(b"\x00" * 10)
        binary_writer.seek(3)

        self.assertEqual(binary_writer.size(), 10)
        self.assertEqual(binary_writer.tell(), 3)


class TestString(unittest.TestCase):
    def test_padded_to_the_field_size(self):
        self.assertEqual(written("string", "ab", 6), b"ab\x00\x00\x00\x00")

    def test_exact_fit_is_not_terminated(self):
        self.assertEqual(written("string", "abcd", 4), b"abcd")

    def test_empty_string(self):
        self.assertEqual(written("string", "", 4), b"\x00\x00\x00\x00")

    def test_zero_size_field(self):
        self.assertEqual(written("string", "", 0), b"")

    def test_custom_padding_byte(self):
        self.assertEqual(written("string", "ab", 5, b"\xFF"), b"ab\xFF\xFF\xFF")

    def test_add_null_byte_appends_after_the_padding(self):
        self.assertEqual(written("string", "ab", 4, add_null_byte=True),
                         b"ab\x00\x00" b"\x00")

    def test_add_null_byte_on_an_exact_fit(self):
        self.assertEqual(written("string", "abcd", 4, add_null_byte=True), b"abcd\x00")

    def test_too_long_is_rejected(self):
        with self.assertRaises(BinaryError):
            written("string", "abcde", 4)

    def test_size_counts_bytes_not_characters(self):
        # "héllo" is 6 bytes in utf-8, so it does not fit in a 5 byte field
        with self.assertRaises(BinaryError):
            written("string", "héllo", 5)
        self.assertEqual(written("string", "héllo", 6), "héllo".encode("utf-8"))

    def test_encoding_from_the_constructor(self):
        binary_writer, stream = writer(encoding="latin-1")
        binary_writer.string("café", 4)
        self.assertEqual(stream.getvalue(), b"caf\xE9")

    def test_encoding_override_per_call(self):
        self.assertEqual(written("string", "café", 4, encoding="latin-1"), b"caf\xE9")

    def test_shift_jis(self):
        self.assertEqual(written("string", "テスト", 6, encoding="shift_jis"),
                         "テスト".encode("shift_jis"))

    def test_unencodable_character(self):
        with self.assertRaises(UnicodeEncodeError):
            written("string", "テスト", 32, encoding="latin-1")


class TestRoundTripWithReader(unittest.TestCase):
    def _roundtrip(self, method: str, value):
        binary_writer, stream = writer()
        getattr(binary_writer, method)(value)
        stream.seek(0)
        return getattr(BinaryReader(stream), method)()

    def test_numeric_roundtrips(self):
        cases = [
            ("u8", 0), ("u8", 255),
            ("u16", 0), ("u16", 65535),
            ("u32", 0), ("u32", 0xFFFFFFFF),
            ("u64", 0), ("u64", 0xFFFFFFFFFFFFFFFF),
            ("s8", -128), ("s8", 127),
            ("s16", -32768), ("s16", 32767),
            ("s32", -2147483648), ("s32", 2147483647),
            ("s64", -(2**63)), ("s64", 2**63 - 1),
            ("float", 0.0), ("float", -1.5), ("float", 1024.0),
            ("u32_le", 0xDEADBEEF),
            ("u32_shifted", 0), ("u32_shifted", 0x8000),
        ]
        for method, value in cases:
            with self.subTest(method=method, value=value):
                self.assertEqual(self._roundtrip(method, value), value)

    def test_list_u32_roundtrip(self):
        binary_writer, stream = writer()
        binary_writer.list_u32([1, 0xFFFFFFFF, 0])
        stream.seek(0)
        self.assertEqual(BinaryReader(stream).list_u32(3), [1, 0xFFFFFFFF, 0])

    def test_string_roundtrip(self):
        binary_writer, stream = writer()
        binary_writer.string("name", 32)
        stream.seek(0)
        self.assertEqual(BinaryReader(stream).string(32), "name")

    def test_string_until_null_roundtrip(self):
        binary_writer, stream = writer()
        binary_writer.string("first", len("first"), add_null_byte=True)
        binary_writer.string("second", len("second"), add_null_byte=True)
        stream.seek(0)

        binary_reader = BinaryReader(stream)
        self.assertEqual(binary_reader.string_until_null(), "first")
        self.assertEqual(binary_reader.string_until_null(), "second")

    def test_mixed_record_roundtrip(self):
        binary_writer, stream = writer()
        binary_writer.u32(0xCAFEBABE)
        binary_writer.s16(-2)
        binary_writer.u8(7)
        binary_writer.pad(1)
        binary_writer.float(2.5)
        binary_writer.string("label", 16)
        binary_writer.list_u32([4, 5])

        stream.seek(0)
        binary_reader = BinaryReader(stream)
        self.assertEqual(binary_reader.u32(), 0xCAFEBABE)
        self.assertEqual(binary_reader.s16(), -2)
        self.assertEqual(binary_reader.u8(), 7)
        binary_reader.skip(1)
        self.assertEqual(binary_reader.float(), 2.5)
        self.assertEqual(binary_reader.string(16), "label")
        self.assertEqual(binary_reader.list_u32(2), [4, 5])
        self.assertEqual(binary_reader.tell(), binary_writer.size())

    def test_reader_and_writer_can_share_one_stream(self):
        stream = BytesIO()
        binary_writer = BinaryWriter(stream)
        binary_reader = BinaryReader(stream)

        binary_writer.u32(0x12345678)
        binary_reader.seek(0)
        self.assertEqual(binary_reader.u32(), 0x12345678)


if __name__ == "__main__":
    unittest.main()