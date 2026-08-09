import unittest
from io import BytesIO

from wiithon.exceptions import BCSVFileError, BinaryError, CorruptedDataError, InvalidFormatError
from wiithon.formats.bcsv import (
    BCSV,
    BCSV_FIELD_SIZE,
    BCSV_HEADER_SIZE,
    BCSVEntry,
    BCSVField,
    BCSVFieldKey,
    BCSVHashKey,
    BCSVKey,
    BCSVNameKey,
    BCSVType,
    BCSVTypeSize,
    calculate_field_hash,
)

# ---------------------------------------------------------------------------
# Hand-written reference file
#
# Header (big-endian, 0x10 bytes)
#   entry_count = 2, field_count = 6, entry_data_offset = 0x58, entry_size = 0x14
#
# Entry layout (0x14 bytes, byte 0x0F is inter-field padding):
#   0x00 LONG | 0x04 UNSIGNED_LONG | 0x08 FLOAT | 0x0C SHORT | 0x0E BYTE
#   0x10 STRING_OFFSET (offset relative to the start of the string pool)
#
# String pool starts at 0x58 + 2 * 0x14 = 0x80, file is padded to a multiple
# of 32 with b"@".
# ---------------------------------------------------------------------------

HASH_LONG = 0xEBF5FD77   # calculate_field_hash("long_field")
HASH_ULONG = 0xF87BAFAC  # calculate_field_hash("ulong_field")
HASH_FLOAT = 0xA856F157  # calculate_field_hash("float_field")
HASH_SHORT = 0x4CC23B77  # calculate_field_hash("short_field")
HASH_BYTE = 0x313E7F03   # calculate_field_hash("byte_field")
HASH_STR = 0xE337996C    # calculate_field_hash("str_field")

REFERENCE_BCSV = (
    # -- header ---------------------------------------------------------
    b"\x00\x00\x00\x02"          # entry_count
    b"\x00\x00\x00\x06"          # field_count
    b"\x00\x00\x00\x58"          # entry_data_offset
    b"\x00\x00\x00\x14"          # entry_size
    # -- fields (hash, bitmask, offset, shift, type) ---------------------
    b"\xEB\xF5\xFD\x77" b"\xFF\xFF\xFF\xFF" b"\x00\x00" b"\x00" b"\x00"  # LONG
    b"\xF8\x7B\xAF\xAC" b"\xFF\xFF\xFF\xFF" b"\x00\x04" b"\x00" b"\x03"  # UNSIGNED_LONG
    b"\xA8\x56\xF1\x57" b"\xFF\xFF\xFF\xFF" b"\x00\x08" b"\x00" b"\x02"  # FLOAT
    b"\x4C\xC2\x3B\x77" b"\x00\x00\xFF\xFF" b"\x00\x0C" b"\x00" b"\x04"  # SHORT
    b"\x31\x3E\x7F\x03" b"\x00\x00\x00\xFF" b"\x00\x0E" b"\x00" b"\x05"  # BYTE
    b"\xE3\x37\x99\x6C" b"\xFF\xFF\xFF\xFF" b"\x00\x10" b"\x00" b"\x06"  # STRING_OFFSET
    # -- entry 0 ---------------------------------------------------------
    b"\xFF\xFF\xFF\xFB"          # -5
    b"\x00\x00\x00\x07"          # 7
    b"\x3F\xC0\x00\x00"          # 1.5
    b"\xFE\xD4"                  # -300
    b"\xFE"                      # -2
    b"\x00"                      # padding
    b"\x00\x00\x00\x00"          # pool offset 0 -> "hello"
    # -- entry 1 ---------------------------------------------------------
    b"\x7F\xFF\xFF\xFF"          # 2147483647
    b"\x00\x00\x00\x00"          # 0
    b"\xBF\x00\x00\x00"          # -0.5
    b"\x7F\xFF"                  # 32767
    b"\x7F"                      # 127
    b"\x00"                      # padding
    b"\x00\x00\x00\x06"          # pool offset 6 -> "world"
    # -- string pool -----------------------------------------------------
    b"hello\x00world\x00"
    # -- padding to a 32 byte boundary -----------------------------------
) + b"@" * 20

REFERENCE_ROWS = [
    {
        str(HASH_LONG): -5,
        str(HASH_ULONG): 7,
        str(HASH_FLOAT): 1.5,
        str(HASH_SHORT): -300,
        str(HASH_BYTE): -2,
        str(HASH_STR): "hello",
    },
    {
        str(HASH_LONG): 2147483647,
        str(HASH_ULONG): 0,
        str(HASH_FLOAT): -0.5,
        str(HASH_SHORT): 32767,
        str(HASH_BYTE): 127,
        str(HASH_STR): "world",
    },
]

FIELD_NAMES = {
    HASH_LONG: "long_field",
    HASH_ULONG: "ulong_field",
    HASH_FLOAT: "float_field",
    HASH_SHORT: "short_field",
    HASH_BYTE: "byte_field",
    HASH_STR: "str_field",
}


def reference_fields() -> list[BCSVField]:
    """The same six fields as REFERENCE_BCSV, built from Python."""
    return [
        BCSVField(HASH_LONG, 0xFFFFFFFF, 0x00, 0, BCSVType.LONG),
        BCSVField(HASH_ULONG, 0xFFFFFFFF, 0x04, 0, BCSVType.UNSIGNED_LONG),
        BCSVField(HASH_FLOAT, 0xFFFFFFFF, 0x08, 0, BCSVType.FLOAT),
        BCSVField(HASH_SHORT, 0x0000FFFF, 0x0C, 0, BCSVType.SHORT),
        BCSVField(HASH_BYTE, 0x000000FF, 0x0E, 0, BCSVType.BYTE),
        BCSVField(HASH_STR, 0xFFFFFFFF, 0x10, 0, BCSVType.STRING_OFFSET),
    ]


def reference_bcsv() -> BCSV:
    fields = reference_fields()
    entries = []
    for row in REFERENCE_ROWS:
        entry = BCSVEntry()
        for field in fields:
            entry[field] = row[field.field_name]
        entries.append(entry)
    return BCSV(fields, entries)


def build_bcsv(fields: list[BCSVField], rows: list[list]) -> BCSV:
    """Builds a BCSV from fields and positional row values."""
    entries = []
    for row in rows:
        entry = BCSVEntry()
        for field, value in zip(fields, row, strict=True):
            entry[field] = value
        entries.append(entry)
    return BCSV(fields, entries)


def pack_header(entry_count: int, field_count: int, entry_data_offset: int, entry_size: int) -> bytes:
    return b"".join(v.to_bytes(4, "big") for v in
                    (entry_count, field_count, entry_data_offset, entry_size))


def pack_field(field_hash: int, bitmask: int, offset: int, shift: int, field_type: int) -> bytes:
    return (field_hash.to_bytes(4, "big") + bitmask.to_bytes(4, "big")
            + offset.to_bytes(2, "big") + bytes([shift, field_type]))


class BCSVTestCase(unittest.TestCase):
    """BCSVEntry.hash_names is class-level state shared by every import."""

    def setUp(self):
        BCSVEntry.hash_names = {}

    def tearDown(self):
        BCSVEntry.hash_names = {}


class TestCalculateFieldHash(unittest.TestCase):
    def test_empty_name(self):
        self.assertEqual(calculate_field_hash(""), 0)

    def test_known_hashes(self):
        self.assertEqual(calculate_field_hash("long_field"), HASH_LONG)
        self.assertEqual(calculate_field_hash("str_field"), HASH_STR)

    def test_single_char(self):
        self.assertEqual(calculate_field_hash("A"), ord("A"))

    def test_stops_on_null_byte(self):
        self.assertEqual(calculate_field_hash("ab\x00cd"), calculate_field_hash("ab"))

    def test_bytes_above_127_are_signed(self):
        # "é" is 0xC3 0xA9 in utf-8, both read as negative chars:
        # ((0 * 0x1F) - 61) * 0x1F - 87 = -1978 -> 0xFFFFF846
        self.assertEqual(calculate_field_hash("é"), 0xFFFFF846)

    def test_result_is_32_bit(self):
        self.assertLess(calculate_field_hash("a_very_long_field_name_to_overflow"), 1 << 32)


class TestBCSVKey(unittest.TestCase):
    def test_str_key(self):
        key = BCSVKey.create("name")
        self.assertIsInstance(key, BCSVNameKey)
        self.assertEqual(key.resolve_name(), "name")

    def test_int_key(self):
        key = BCSVKey.create(HASH_LONG)
        self.assertIsInstance(key, BCSVHashKey)
        self.assertEqual(key.resolve_name(), str(HASH_LONG))

    def test_field_key(self):
        field = BCSVField(HASH_LONG, 0xFFFFFFFF, 0, 0, BCSVType.LONG)
        key = BCSVKey.create(field)
        self.assertIsInstance(key, BCSVFieldKey)
        self.assertEqual(key.resolve_name(), str(HASH_LONG))

    def test_unsupported_key_type(self):
        with self.assertRaises(TypeError):
            BCSVKey.create(1.5)


class TestBCSVEntry(unittest.TestCase):
    def setUp(self):
        self.field = BCSVField(HASH_LONG, 0xFFFFFFFF, 0, 0, BCSVType.LONG)
        self.entry = BCSVEntry()
        self.entry[self.field] = 12

    def test_lookup_by_field_hash_and_name(self):
        self.assertEqual(self.entry[self.field], 12)
        self.assertEqual(self.entry[HASH_LONG], 12)
        self.assertEqual(self.entry[str(HASH_LONG)], 12)

    def test_accepted_value_types(self):
        for value in (1, "text", 1.5):
            with self.subTest(value=value):
                self.entry[self.field] = value
                self.assertEqual(self.entry[self.field], value)

    def test_rejects_non_bcsv_value(self):
        with self.assertRaises(TypeError):
            self.entry[self.field] = [1, 2, 3]

    def test_rejects_unsupported_key(self):
        with self.assertRaises(TypeError):
            self.entry[1.5] = 1


class TestBCSVField(unittest.TestCase):
    def test_import_export_field_roundtrip(self):
        raw = pack_field(HASH_SHORT, 0x0000FF00, 0x000C, 8, BCSVType.SHORT)
        field = BCSVField.import_field(BytesIO(raw))

        self.assertEqual(field.field_hash, HASH_SHORT)
        self.assertEqual(field.field_bitmask, 0x0000FF00)
        self.assertEqual(field.field_offset, 0x000C)
        self.assertEqual(field.field_shift, 8)
        self.assertEqual(field.field_type, BCSVType.SHORT)
        self.assertEqual(field.export_field(), raw)
        self.assertEqual(len(raw), BCSV_FIELD_SIZE)

    def test_default_field_name_is_the_stringified_hash(self):
        self.assertEqual(BCSVField(42, 0, 0, 0, BCSVType.LONG).field_name, "42")

    def test_unknown_field_type(self):
        with self.assertRaises(ValueError):
            BCSVField(1, 0, 0, 0, 99)

    def test_field_sizes(self):
        sizes = {
            BCSVType.LONG: BCSVTypeSize.WORD,
            BCSVType.UNSIGNED_LONG: BCSVTypeSize.WORD,
            BCSVType.FLOAT: BCSVTypeSize.WORD,
            BCSVType.STRING_OFFSET: BCSVTypeSize.WORD,
            BCSVType.SHORT: BCSVTypeSize.HALF_WORD,
            BCSVType.BYTE: BCSVTypeSize.BYTE,
            BCSVType.STRING: BCSVTypeSize.STRING,
        }
        for field_type, expected in sizes.items():
            with self.subTest(field_type=field_type):
                field = BCSVField(1, 0xFFFFFFFF, 0, 0, field_type)
                self.assertEqual(field.get_field_size(), expected)


class TestImportHandWritten(BCSVTestCase):
    def test_import_reference_file(self):
        bcsv = BCSV.import_bcsv(BytesIO(REFERENCE_BCSV))

        self.assertEqual(len(bcsv.fields), 6)
        self.assertEqual(len(bcsv.entries), 2)
        self.assertEqual([dict(entry) for entry in bcsv.entries], REFERENCE_ROWS)

    def test_imported_fields_match_the_header_block(self):
        bcsv = BCSV.import_bcsv(BytesIO(REFERENCE_BCSV))

        self.assertEqual([f.field_hash for f in bcsv.fields],
                         [HASH_LONG, HASH_ULONG, HASH_FLOAT, HASH_SHORT, HASH_BYTE, HASH_STR])
        self.assertEqual([f.field_offset for f in bcsv.fields],
                         [0x00, 0x04, 0x08, 0x0C, 0x0E, 0x10])
        self.assertEqual([f.field_type for f in bcsv.fields],
                         [BCSVType.LONG, BCSVType.UNSIGNED_LONG, BCSVType.FLOAT,
                          BCSVType.SHORT, BCSVType.BYTE, BCSVType.STRING_OFFSET])

    def test_import_does_not_consume_the_caller_stream_position(self):
        stream = BytesIO(REFERENCE_BCSV)
        stream.seek(0x40)  # import must not depend on the incoming position
        bcsv = BCSV.import_bcsv(stream)
        self.assertEqual(len(bcsv.entries), 2)

    def test_field_names_mapping(self):
        bcsv = BCSV.import_bcsv(BytesIO(REFERENCE_BCSV), field_names=FIELD_NAMES)

        self.assertEqual([f.field_name for f in bcsv.fields], list(FIELD_NAMES.values()))
        self.assertEqual(bcsv.entries[0]["long_field"], -5)
        self.assertEqual(bcsv.entries[1]["str_field"], "world")

    def test_calculated_entry_size_matches_the_header(self):
        bcsv = BCSV.import_bcsv(BytesIO(REFERENCE_BCSV))
        self.assertEqual(bcsv.calculate_data_entry_size(), 0x14)

    def test_import_without_entries(self):
        raw = (pack_header(0, 1, 0x1C, 4)
               + pack_field(HASH_LONG, 0xFFFFFFFF, 0, 0, BCSVType.LONG))
        bcsv = BCSV.import_bcsv(BytesIO(raw))

        self.assertEqual(len(bcsv.fields), 1)
        self.assertEqual(bcsv.entries, [])


class TestImportErrors(BCSVTestCase):
    def test_buffer_shorter_than_the_header(self):
        with self.assertRaises(InvalidFormatError):
            BCSV.import_bcsv(BytesIO(b"\x00" * (BCSV_HEADER_SIZE - 1)))

    def test_field_block_not_a_multiple_of_the_field_size(self):
        # entry_data_offset leaves 13 bytes of field block for 1 field
        raw = pack_header(0, 1, BCSV_HEADER_SIZE + 13, 4) + b"\x00" * 13
        with self.assertRaises(CorruptedDataError):
            BCSV.import_bcsv(BytesIO(raw))

    def test_declared_field_count_does_not_match_the_block_size(self):
        # room for 2 fields but the header announces 1
        raw = pack_header(0, 1, BCSV_HEADER_SIZE + 2 * BCSV_FIELD_SIZE, 4) + b"\x00" * 24
        with self.assertRaises(CorruptedDataError):
            BCSV.import_bcsv(BytesIO(raw))

    def test_entry_block_larger_than_the_file(self):
        raw = (pack_header(4, 1, 0x1C, 4)
               + pack_field(HASH_LONG, 0xFFFFFFFF, 0, 0, BCSVType.LONG)
               + b"\x00" * 4)  # only 1 entry present, 4 announced
        with self.assertRaises(CorruptedDataError):
            BCSV.import_bcsv(BytesIO(raw))


class TestExportHandWritten(BCSVTestCase):
    def test_export_matches_the_reference_bytes(self):
        self.assertEqual(reference_bcsv().export_bcsv().getvalue(), REFERENCE_BCSV)

    def test_export_pads_to_a_32_byte_boundary_with_at_signs(self):
        raw = reference_bcsv().export_bcsv().getvalue()
        self.assertEqual(len(raw) % 32, 0)
        self.assertTrue(raw.endswith(b"@"))

    def test_export_without_entries(self):
        bcsv = BCSV(reference_fields(), [])
        raw = bcsv.export_bcsv().getvalue()

        self.assertEqual(raw[0:4], b"\x00\x00\x00\x00")   # entry_count
        self.assertEqual(raw[4:8], b"\x00\x00\x00\x06")   # field_count
        self.assertEqual(raw[8:12], b"\x00\x00\x00\x58")  # entry_data_offset
        self.assertEqual(len(raw) % 32, 0)

    def test_export_rejects_a_non_field(self):
        bcsv = reference_bcsv()
        bcsv.fields.append("not a field")
        with self.assertRaises(BCSVFileError):
            bcsv.export_bcsv()

    def test_export_rejects_a_non_entry(self):
        bcsv = reference_bcsv()
        bcsv.entries.append({"1": 2})
        with self.assertRaises(BCSVFileError):
            bcsv.export_bcsv()


class TestRoundTrip(BCSVTestCase):
    def test_bytes_roundtrip(self):
        bcsv = BCSV.import_bcsv(BytesIO(REFERENCE_BCSV))
        self.assertEqual(bcsv.export_bcsv().getvalue(), REFERENCE_BCSV)

    def test_object_roundtrip(self):
        original = reference_bcsv()
        reloaded = BCSV.import_bcsv(BytesIO(original.export_bcsv().getvalue()))
        self.assertEqual([dict(e) for e in reloaded.entries], REFERENCE_ROWS)

    def test_double_roundtrip_is_stable(self):
        once = BCSV.import_bcsv(BytesIO(REFERENCE_BCSV)).export_bcsv().getvalue()
        twice = BCSV.import_bcsv(BytesIO(once)).export_bcsv().getvalue()
        self.assertEqual(once, twice)
        self.assertEqual(twice, REFERENCE_BCSV)

    def test_write_read_roundtrip(self):
        stream = BytesIO()
        reference_bcsv().write(stream)
        stream.seek(0)

        reloaded = BCSV.read(stream)
        self.assertEqual([dict(e) for e in reloaded.entries], REFERENCE_ROWS)

    def test_roundtrip_after_editing_a_value(self):
        bcsv = BCSV.import_bcsv(BytesIO(REFERENCE_BCSV))
        bcsv.entries[0][HASH_LONG] = 1234
        bcsv.entries[0][HASH_STR] = "edited"

        reloaded = BCSV.import_bcsv(BytesIO(bcsv.export_bcsv().getvalue()))
        self.assertEqual(reloaded.entries[0][HASH_LONG], 1234)
        self.assertEqual(reloaded.entries[0][HASH_STR], "edited")
        self.assertEqual(reloaded.entries[1][HASH_STR], "world")


class TestNumericEdgeCases(BCSVTestCase):
    def _roundtrip_single(self, field: BCSVField, value):
        bcsv = build_bcsv([field], [[value]])
        reloaded = BCSV.import_bcsv(BytesIO(bcsv.export_bcsv().getvalue()))
        return reloaded.entries[0][field.field_name]

    def test_long_bounds(self):
        field = BCSVField(HASH_LONG, 0xFFFFFFFF, 0, 0, BCSVType.LONG)
        for value in (-2147483648, -1, 0, 1, 2147483647):
            with self.subTest(value=value):
                self.assertEqual(self._roundtrip_single(field, value), value)

    def test_short_bounds(self):
        field = BCSVField(HASH_SHORT, 0xFFFF, 0, 0, BCSVType.SHORT)
        for value in (-32768, -1, 0, 32767):
            with self.subTest(value=value):
                self.assertEqual(self._roundtrip_single(field, value), value)

    def test_byte_bounds(self):
        field = BCSVField(HASH_BYTE, 0xFF, 0, 0, BCSVType.BYTE)
        for value in (-128, -1, 0, 127):
            with self.subTest(value=value):
                self.assertEqual(self._roundtrip_single(field, value), value)

    def test_float_values(self):
        field = BCSVField(HASH_FLOAT, 0xFFFFFFFF, 0, 0, BCSVType.FLOAT)
        for value in (0.0, -0.5, 1.5, 1024.0, -65536.0):
            with self.subTest(value=value):
                self.assertEqual(self._roundtrip_single(field, value), value)

    def test_float_precision_is_32_bit(self):
        field = BCSVField(HASH_FLOAT, 0xFFFFFFFF, 0, 0, BCSVType.FLOAT)
        # 0.1 is not representable in 32-bit, it must come back rounded
        self.assertAlmostEqual(self._roundtrip_single(field, 0.1), 0.1, places=6)

class TestBitmaskAndShift(BCSVTestCase):
    """Three sub-fields packed into a single 32-bit word."""

    def setUp(self):
        super().setUp()
        self.fields = [
            BCSVField(0x0A, 0x0000000F, 0, 0, BCSVType.LONG),
            BCSVField(0x0B, 0x000000F0, 0, 4, BCSVType.LONG),
            BCSVField(0x0C, 0xFFFFFF00, 0, 8, BCSVType.LONG),
        ]

    def test_packed_word_layout(self):
        raw = build_bcsv(self.fields, [[0xA, 0x5, 0x1234]]).export_bcsv().getvalue()

        entry_data_offset = 0x10 + 3 * BCSV_FIELD_SIZE
        word = raw[entry_data_offset:entry_data_offset + 4]
        self.assertEqual(word, b"\x00\x12\x34\x5A")

    def test_packed_word_roundtrip(self):
        bcsv = build_bcsv(self.fields, [[0xA, 0x5, 0x1234]])
        reloaded = BCSV.import_bcsv(BytesIO(bcsv.export_bcsv().getvalue()))

        self.assertEqual(reloaded.entries[0]["10"], 0xA)
        self.assertEqual(reloaded.entries[0]["11"], 0x5)
        self.assertEqual(reloaded.entries[0]["12"], 0x1234)

    def test_value_is_truncated_by_its_bitmask(self):
        # 0xFF does not fit in the 4-bit mask, only the low nibble survives
        bcsv = build_bcsv([self.fields[0]], [[0xFF]])
        reloaded = BCSV.import_bcsv(BytesIO(bcsv.export_bcsv().getvalue()))
        self.assertEqual(reloaded.entries[0]["10"], 0xF)

    def test_packed_short_and_byte(self):
        fields = [
            BCSVField(0x20, 0x00FF, 0, 0, BCSVType.SHORT),
            BCSVField(0x21, 0xFF00, 0, 8, BCSVType.SHORT),
            BCSVField(0x22, 0x0F, 2, 0, BCSVType.BYTE),
            BCSVField(0x23, 0xF0, 2, 4, BCSVType.BYTE),
        ]
        bcsv = build_bcsv(fields, [[0x12, 0x34, 0x5, 0x6]])
        reloaded = BCSV.import_bcsv(BytesIO(bcsv.export_bcsv().getvalue()))

        self.assertEqual(reloaded.entries[0]["32"], 0x12)
        self.assertEqual(reloaded.entries[0]["33"], 0x34)
        self.assertEqual(reloaded.entries[0]["34"], 0x5)
        self.assertEqual(reloaded.entries[0]["35"], 0x6)


class TestStringOffset(BCSVTestCase):
    def setUp(self):
        super().setUp()
        self.field = BCSVField(HASH_STR, 0xFFFFFFFF, 0, 0, BCSVType.STRING_OFFSET)
        self.pool_start = 0x10 + BCSV_FIELD_SIZE + 4  # header + 1 field + 1 entry

    def _pool(self, raw: bytes, entry_count: int = 1) -> bytes:
        start = 0x10 + BCSV_FIELD_SIZE + 4 * entry_count
        return raw[start:].rstrip(b"@")

    def test_single_string(self):
        raw = build_bcsv([self.field], [["hello"]]).export_bcsv().getvalue()

        self.assertEqual(self._pool(raw), b"hello\x00")
        self.assertEqual(raw[self.pool_start - 4:self.pool_start], b"\x00\x00\x00\x00")

    def test_pool_offsets_are_relative_to_the_pool_start(self):
        raw = build_bcsv([self.field], [["hello"], ["world"]]).export_bcsv().getvalue()

        self.assertEqual(self._pool(raw, entry_count=2), b"hello\x00world\x00")
        entries = raw[0x10 + BCSV_FIELD_SIZE:0x10 + BCSV_FIELD_SIZE + 8]
        self.assertEqual(entries, b"\x00\x00\x00\x00" b"\x00\x00\x00\x06")

    def test_identical_strings_are_pooled_once(self):
        raw = build_bcsv([self.field], [["same"], ["same"]]).export_bcsv().getvalue()

        self.assertEqual(self._pool(raw, entry_count=2), b"same\x00")
        entries = raw[0x10 + BCSV_FIELD_SIZE:0x10 + BCSV_FIELD_SIZE + 8]
        self.assertEqual(entries, b"\x00\x00\x00\x00" b"\x00\x00\x00\x00")

    def test_empty_string(self):
        bcsv = build_bcsv([self.field], [[""]])
        raw = bcsv.export_bcsv().getvalue()

        self.assertEqual(self._pool(raw), b"\x00")
        reloaded = BCSV.import_bcsv(BytesIO(raw))
        self.assertEqual(reloaded.entries[0][HASH_STR], "")

    def test_shared_offsets_in_a_hand_written_file(self):
        # both entries point at pool offset 0
        raw = (pack_header(2, 1, 0x1C, 4)
               + pack_field(HASH_STR, 0xFFFFFFFF, 0, 0, BCSVType.STRING_OFFSET)
               + b"\x00\x00\x00\x00"
               + b"\x00\x00\x00\x00"
               + b"shared\x00")
        bcsv = BCSV.import_bcsv(BytesIO(raw))

        self.assertEqual(bcsv.entries[0][HASH_STR], "shared")
        self.assertEqual(bcsv.entries[1][HASH_STR], "shared")

    def test_offset_into_the_middle_of_a_pooled_string(self):
        # "prefix" and "fix" can legally share storage in a real file
        raw = (pack_header(2, 1, 0x1C, 4)
               + pack_field(HASH_STR, 0xFFFFFFFF, 0, 0, BCSVType.STRING_OFFSET)
               + b"\x00\x00\x00\x00"
               + b"\x00\x00\x00\x03"
               + b"prefix\x00")
        bcsv = BCSV.import_bcsv(BytesIO(raw))

        self.assertEqual(bcsv.entries[0][HASH_STR], "prefix")
        self.assertEqual(bcsv.entries[1][HASH_STR], "fix")

    def test_long_string(self):
        value = "x" * 300
        bcsv = build_bcsv([self.field], [[value]])
        reloaded = BCSV.import_bcsv(BytesIO(bcsv.export_bcsv().getvalue()))
        self.assertEqual(reloaded.entries[0][HASH_STR], value)

    def test_non_string_value_is_stringified(self):
        bcsv = build_bcsv([self.field], [[42]])
        reloaded = BCSV.import_bcsv(BytesIO(bcsv.export_bcsv().getvalue()))
        self.assertEqual(reloaded.entries[0][HASH_STR], "42")


class TestEmbeddedString(BCSVTestCase):
    """BCSVType.STRING: 32 bytes stored inline in the entry (deprecated)."""

    def setUp(self):
        super().setUp()
        self.field = BCSVField(HASH_STR, 0xFFFFFFFF, 0, 0, BCSVType.STRING)

    def test_roundtrip(self):
        bcsv = build_bcsv([self.field], [["embedded"]])
        reloaded = BCSV.import_bcsv(BytesIO(bcsv.export_bcsv().getvalue()))
        self.assertEqual(reloaded.entries[0][HASH_STR], "embedded")

    def test_entry_size_is_32_bytes(self):
        self.assertEqual(build_bcsv([self.field], []).calculate_data_entry_size(), 32)

    def test_written_field_is_null_padded(self):
        raw = build_bcsv([self.field], [["ab"]]).export_bcsv().getvalue()
        start = 0x10 + BCSV_FIELD_SIZE
        self.assertEqual(raw[start:start + 32], b"ab" + b"\x00" * 30)

    def test_exactly_32_bytes_has_no_terminator(self):
        value = "y" * 32
        bcsv = build_bcsv([self.field], [[value]])
        reloaded = BCSV.import_bcsv(BytesIO(bcsv.export_bcsv().getvalue()))
        self.assertEqual(reloaded.entries[0][HASH_STR], value)

    def test_too_long_string_is_rejected(self):
        with self.assertRaises(BinaryError):
            build_bcsv([self.field], [["z" * 33]]).export_bcsv()

    def test_hand_written_field_stops_at_the_first_null(self):
        raw = (pack_header(1, 1, 0x1C, 32)
               + pack_field(HASH_STR, 0xFFFFFFFF, 0, 0, BCSVType.STRING)
               + b"name\x00" + b"\xFF" * 27)  # trailing junk after the null
        bcsv = BCSV.import_bcsv(BytesIO(raw))
        self.assertEqual(bcsv.entries[0][HASH_STR], "name")


class TestEncodings(BCSVTestCase):
    def test_utf8_multibyte_pool_offsets_count_bytes(self):
        field = BCSVField(HASH_STR, 0xFFFFFFFF, 0, 0, BCSVType.STRING_OFFSET)
        bcsv = build_bcsv([field], [["héllo"], ["ok"]])
        raw = bcsv.export_bcsv().getvalue()

        entries = raw[0x10 + BCSV_FIELD_SIZE:0x10 + BCSV_FIELD_SIZE + 8]
        # "héllo" is 6 bytes in utf-8, so the second string starts at 7
        self.assertEqual(entries, b"\x00\x00\x00\x00" b"\x00\x00\x00\x07")

        reloaded = BCSV.import_bcsv(BytesIO(raw))
        self.assertEqual([e[HASH_STR] for e in reloaded.entries], ["héllo", "ok"])

    def test_shift_jis_string_offset(self):
        field = BCSVField(HASH_STR, 0xFFFFFFFF, 0, 0, BCSVType.STRING_OFFSET)
        bcsv = build_bcsv([field], [["テスト"]])
        raw = bcsv.export_bcsv(str_fmt="shift_jis").getvalue()

        self.assertIn("テスト".encode("shift_jis"), raw)
        reloaded = BCSV.import_bcsv(BytesIO(raw), str_fmt="shift_jis")
        self.assertEqual(reloaded.entries[0][HASH_STR], "テスト")

    def test_shift_jis_embedded_string(self):
        field = BCSVField(HASH_STR, 0xFFFFFFFF, 0, 0, BCSVType.STRING)
        bcsv = build_bcsv([field], [["テスト"]])
        raw = bcsv.export_bcsv(str_fmt="shift_jis").getvalue()

        start = 0x10 + BCSV_FIELD_SIZE
        self.assertEqual(raw[start:start + 6], "テスト".encode("shift_jis"))
        reloaded = BCSV.import_bcsv(BytesIO(raw), str_fmt="shift_jis")
        self.assertEqual(reloaded.entries[0][HASH_STR], "テスト")

    def test_latin1_string_offset(self):
        field = BCSVField(HASH_STR, 0xFFFFFFFF, 0, 0, BCSVType.STRING_OFFSET)
        bcsv = build_bcsv([field], [["café"]])
        raw = bcsv.export_bcsv(str_fmt="latin-1").getvalue()

        self.assertIn(b"caf\xe9\x00", raw)
        reloaded = BCSV.import_bcsv(BytesIO(raw), str_fmt="latin-1")
        self.assertEqual(reloaded.entries[0][HASH_STR], "café")

    def test_write_uses_the_encoding_kept_on_the_object(self):
        field = BCSVField(HASH_STR, 0xFFFFFFFF, 0, 0, BCSVType.STRING_OFFSET)
        bcsv = build_bcsv([field], [["café"]])
        bcsv.str_fmt = "latin-1"

        stream = BytesIO()
        bcsv.write(stream)
        self.assertIn(b"caf\xe9\x00", stream.getvalue())


class TestFieldAndEntryManagement(BCSVTestCase):
    def test_add_field_fills_existing_entries(self):
        bcsv = reference_bcsv()
        new_field = BCSVField(0x1234, 0xFFFFFFFF, 0x14, 0, BCSVType.LONG)
        bcsv.add_bcsv_field(new_field, 99)

        self.assertEqual(len(bcsv.fields), 7)
        self.assertTrue(all(entry[new_field] == 99 for entry in bcsv.entries))
        self.assertEqual(bcsv.calculate_data_entry_size(), 0x18)

    def test_add_field_then_roundtrip(self):
        bcsv = reference_bcsv()
        bcsv.add_bcsv_field(BCSVField(0x1234, 0xFFFFFFFF, 0x14, 0, BCSVType.LONG), 99)

        reloaded = BCSV.import_bcsv(BytesIO(bcsv.export_bcsv().getvalue()))
        self.assertEqual(reloaded.entries[0]["4660"], 99)
        self.assertEqual(reloaded.entries[0][HASH_STR], "hello")

    def test_add_duplicate_field(self):
        bcsv = reference_bcsv()
        with self.assertRaises(BCSVFileError):
            bcsv.add_bcsv_field(BCSVField(HASH_LONG, 0xFFFFFFFF, 0x14, 0, BCSVType.LONG), 0)

    def test_remove_field(self):
        bcsv = reference_bcsv()
        bcsv.remove_bcsv_field(HASH_FLOAT)

        self.assertEqual(len(bcsv.fields), 5)
        self.assertNotIn(str(HASH_FLOAT), bcsv.entries[0])

    def test_remove_unknown_field(self):
        with self.assertRaises(ValueError):
            reference_bcsv().remove_bcsv_field("nope")

    def test_add_entry_requires_fields(self):
        entry = BCSVEntry()
        entry["1"] = 1
        with self.assertRaises(KeyError):
            BCSV().add_bcsv_entry(entry)

    def test_add_empty_entry(self):
        with self.assertRaises(ValueError):
            BCSV(reference_fields(), []).add_bcsv_entry(BCSVEntry())

    def test_remove_entry_by_index_and_by_object(self):
        bcsv = reference_bcsv()
        kept = bcsv.entries[1]

        bcsv.remove_bcsv_entry(0)
        self.assertEqual(bcsv.entries, [kept])

        bcsv.remove_bcsv_entry(kept)
        self.assertEqual(bcsv.entries, [])

    def test_remove_entry_with_a_bad_type(self):
        with self.assertRaises(ValueError):
            reference_bcsv().remove_bcsv_entry("0")

    def test_constructor_rejects_bad_fields(self):
        with self.assertRaises(BCSVFileError):
            BCSV(["not a field"], [])

    def test_constructor_rejects_bad_entries(self):
        with self.assertRaises(BCSVFileError):
            BCSV(reference_fields(), [{"1": 2}])

    def test_empty_bcsv_defaults(self):
        bcsv = BCSV()
        self.assertEqual(bcsv.fields, [])
        self.assertEqual(bcsv.entries, [])


if __name__ == "__main__":
    unittest.main()