from enum import IntEnum
from io import BytesIO
from typing import NamedTuple

import wiithon.helpers.Utils as fh

BCSV_HEADER_SIZE: int = 0x10
BCSV_FIELD_SIZE: int = 0xC
BCSV_MAX_STRING_LENGTH: int = 0x20

STRING_FORMAT: str = "utf-8"

type BCSVKey = int | str | BCSVField
type BCSVValue = int | str | float


class BCSVFileError(Exception):
    """Thrown when an error occurs while parsing/writing BCSV data."""
    pass


def calculate_field_hash(field_name: str) -> int:
    """
    Field names are stored internally in RAM for GC/Wii games as hashes, as they are faster lookup tables. So, we will
    calculate the hast and the resulting hash is a 32-bit value.

    Args:
        field_name (str): name of the field to calculate a hash for.
    """
    field_hash: int = 0

    for ch in field_name.encode(STRING_FORMAT):
        if ch == b"\x00":
            break
        ch = ch - 256 if ch >= 128 else ch
        field_hash = (field_hash * 0x1F) + ch

    return field_hash & 0xFFFFFFFF


class BCSVType(IntEnum):
    """
    Indicates the type of data that will be stored in each field type.
    Strings are deprecated and should use of type STRING_OFFSET instead.
    Longs, Short, and Byte should all AND the read value with the field's bitmask and then
        shift the result by the field's shift amount.
    LONG and UNSIGNED_LONG are 32-bit integers. (Signedness not specified, as it can be both)
    FLOAT are 32-bit. (Signedness not specified, as it can be both)
    Short are 16-bit integers (Signedness not specified, as it can be both)
    BYTE is single char/8-bit integers (Signedness not specified, as it can be both)
    Floats are read and written as is.
    String_Offset return the offset from the start of the string pool table where the string can be found.
    """
    LONG = 0 # 32-bit integer.
    STRING = 1 # Embedded string. Deprecated.
    FLOAT = 2 # Single-precision floating-point value.
    UNSIGNED_LONG = 3 # 32-bit integer.
    SHORT = 4 # 16-bit integer.
    BYTE = 5 # Single char/8-bit integers
    STRING_OFFSET = 6 # 32-bit offset into string table.


class BCSVTypeSize(IntEnum):
    """Returns the size of the field based on its BCSVType."""
    WORD = 4
    HALF_WORD = 2
    BYTE = 1
    STRING = 32


class StringPoolElement(NamedTuple):
    """Contains a single element when writing to the output string pool table."""
    value: str
    offset: int


class BCSVField:
    """
    Represents a singular field of data in a BCSV file. Similar to a column in a data table.
    Fields are indexed by hashes and its named are defaulted to its hash stringified, however a
        field_hash->name converter function is provided.

    BCSV File Headers are comprised of 12 bytes in total.
    The first 4 bytes represent the field's hash. Currently, it is unknown how a field's name becomes a hash.
    The second 4 bytes represent the field's bitmask.
    The next 2 bytes represent the starting byte for the field within a given data line in the BCSV file.
    The second to last byte represents shift amount used on the field's value.
    The last byte represents the data type, see BCSVType for value -> type conversion.
    """
    field_hash: int = 0
    field_name: str = None
    field_bitmask: int = 0
    field_offset: int = 0
    field_shift: int = 0
    field_type: BCSVType = None


    def __init__(self, field_hash: int, field_bitmask: int, field_offset: int, data_shift: int, data_type: int):
        """
        Represents a single field/header of a BCSV file.
        
        Args:
            field_hash (int): 32-bit unsigned integer hash of a given field
            field_bitmask (int): 32-bit unsigned integer bitmask, can be 0
            field_offset (int): 16-bit unsigned integer offset within a given BCSV row to load data
            data_shift (int): 8-bit unsigned integer to shift a read value with
            data_type (int): 8-bit unsigned integer to signify the data value. See BCSVType
        """
        self.field_hash = field_hash
        self.field_name = str(self.field_hash)
        self.field_bitmask = field_bitmask
        self.field_offset = field_offset
        self.field_shift = data_shift
        self.field_type = BCSVType(data_type)


    @classmethod
    def import_field(cls, raw_bytes: BytesIO):
        """
        Creates a given field/header from the raw BytesIO (should be 12 bytes)

        Args:
            raw_bytes (BytesIO): Field bytes
        """
        field_hash: int = fh.read_u32(raw_bytes, 0x0)
        field_bitmask: int = fh.read_u32(raw_bytes, 0x4)
        field_offset: int = fh.read_u16(raw_bytes, 0x8)
        field_shift: int = fh.read_u8(raw_bytes, 0xA)
        field_type: int = fh.read_u8(raw_bytes, 0xB)
        return cls(field_hash, field_bitmask, field_offset, field_shift, field_type)


    def export_field(self) -> bytes:
        """Exports a given field back to bytes (size: 0xC)"""
        field_bytes: BytesIO = BytesIO()
        fh.write_u32(field_bytes, self.field_hash, 0x0)
        fh.write_u32(field_bytes, self.field_bitmask, 0x4)
        fh.write_u16(field_bytes, self.field_offset, 0x8)
        fh.write_u8(field_bytes, self.field_shift, 0xA)
        fh.write_u8(field_bytes, self.field_type, 0xB)
        return field_bytes.getvalue()


    def get_value_from_bytes(self, entry_bytes: BytesIO, str_fmt: str = STRING_FORMAT, error_handling: str = "strict") -> BCSVValue | None:
        """
        Gets the field's value from a given BCSV entry's bytes.
        
        Args:
            entry_bytes (BytesIO): Given BCSV entry/row data.
            str_fmt (str): Output decoding format.
            error_handling (str): See decode's "errors" field
        """
        value: int | None = None
        match self.field_type:
            case BCSVType.LONG | BCSVType.UNSIGNED_LONG:
                value = fh.read_s32(entry_bytes, self.field_offset)
                if self.field_bitmask == 0xFFFFFFFF and self.field_shift == 0:
                    return value
            case BCSVType.SHORT:
                value = fh.read_s16(entry_bytes, self.field_offset)
                if self.field_bitmask == 0xFFFF and self.field_shift == 0:
                    return value
            case BCSVType.BYTE:
                value = fh.read_s8(entry_bytes, self.field_offset)
                if self.field_bitmask == 0xFF and self.field_shift == 0:
                    return value
            case BCSVType.FLOAT:
                return fh.read_float(entry_bytes, self.field_offset)
            case BCSVType.STRING_OFFSET:
                return fh.read_u32(entry_bytes, self.field_offset)
            case BCSVType.STRING:
                return fh.read_string(entry_bytes, BCSV_MAX_STRING_LENGTH, self.field_offset, str_fmt, error_handling)
            case _:
                raise TypeError(f"Unsupported BCSV Field type: {self.field_type}")

        return (value & self.field_bitmask) >> self.field_shift


    def set_value_in_buffer(self, entry_bytes: BytesIO, entry_value: BCSVValue, string_pool: list[StringPoolElement], str_fmt: str = STRING_FORMAT):
        """
        Sets the field's value into a given BCSV entry's bytes.
        
        Args:
            entry_bytes (BytesIO): Given BCSV entry/row data.
            entry_value (BCSVValue): Value to transwer back to bytes.
            string_pool (list[StringPoolElement]): List of strings to write back into the string pool
            str_fmt (str): Encoding format.
        """
        match self.field_type:
            case BCSVType.LONG | BCSVType.UNSIGNED_LONG:
                value = entry_value
                if not (self.field_bitmask == 0xFFFFFFFF and self.field_shift == 0):
                    value: int = fh.read_s32(entry_bytes, self.field_offset)
                    value |= (int(entry_value) << int(self.field_shift)) & int(self.field_bitmask)
                fh.write_s32(entry_bytes, value, self.field_offset)
            case BCSVType.SHORT:
                value = entry_value
                if not (self.field_bitmask == 0xFFFF and self.field_shift == 0):
                    value: int = fh.read_s16(entry_bytes, self.field_offset)
                    value |= (int(entry_value) << int(self.field_shift)) & int(self.field_bitmask)
                fh.write_s16(entry_bytes, value, self.field_offset)
            case BCSVType.BYTE:
                value = entry_value
                if not (self.field_bitmask == 0xFF and self.field_shift == 0):
                    value: int = fh.read_s8(entry_bytes, self.field_offset)
                    value |= (int(entry_value) << int(self.field_shift)) & int(self.field_bitmask)
                fh.write_s8(entry_bytes, value, self.field_offset)
            case BCSVType.FLOAT:
                fh.write_float(entry_bytes, float(entry_value), self.field_offset)
            case BCSVType.STRING:
                fh.write_string(entry_bytes, str(entry_value), BCSVTypeSize.STRING, offset=self.field_offset, str_fmt=str_fmt)
            case BCSVType.STRING_OFFSET:
                value: str = str(entry_value)
                pool_element: StringPoolElement = next((element for element in string_pool if
                    element.value == value), None)
                if pool_element is None:
                    pool_offset: int = 0
                    if string_pool:
                        highest_pair: StringPoolElement = string_pool[-1]
                        # + 1 because null byte terminated
                        pool_offset: int = highest_pair.offset + len(highest_pair.value) + 1

                    pool_element = StringPoolElement(value, pool_offset)
                    string_pool.append(pool_element)

                fh.write_s32(entry_bytes, pool_element.offset, self.field_offset)
            case _:
                raise TypeError(f"Unsupported BCSV Field type: {self.field_type}")


    def get_field_size(self):
        """Gets the expected field size of a BCSVValue type."""
        match self.field_type:
            case BCSVType.LONG | BCSVType.UNSIGNED_LONG | BCSVType.FLOAT | BCSVType.STRING_OFFSET:
                return BCSVTypeSize.WORD
            case BCSVType.SHORT:
                return BCSVTypeSize.HALF_WORD
            case BCSVType.BYTE:
                return BCSVTypeSize.BYTE
            case BCSVType.STRING:
                return BCSVTypeSize.STRING
            case _:
                raise TypeError(f"Unsupported BCSV Field type: {self.field_type}")

class BCSVEntry(dict[BCSVKey, BCSVValue]):
    """BCSV entry class which allows for lookup as a string, int (field hash), or as a field directly."""
    hash_names: dict[int, str] = {}

    @staticmethod
    def find_field(bcsv_field: BCSVKey) -> str | None:
        """
        Finds a specific BCSV field by its hash value or field name. Can return None as well if no field found.
        
        Args:
            bcsv_field (BCSVKey): Key used find the related BCSVField
        """
        if isinstance(bcsv_field, int):
            return BCSVEntry.hash_names[bcsv_field] if bcsv_field in BCSVEntry.hash_names else str(bcsv_field)
        elif isinstance(bcsv_field, str):
            return bcsv_field
        elif isinstance(bcsv_field, BCSVField):
            return bcsv_field.field_name
        else:
            return None


    def __getitem__(self, key: BCSVKey) -> BCSVValue:
        """
        Gets a given BCSVValue from a given key. Calls find_field to verify the field exists first.
        
        Args:
            key (BCSVKey): Key used find the related field's value
        """
        field_name: str = BCSVEntry.find_field(key)
        return super().__getitem__(field_name)


    def __setitem__(self, key: BCSVKey, value: BCSVValue):
        """
        Sets a given BCSVValue from a given key. Calls find_field to verify the field exists first.
        
        Args:
            key (BCSVKey): Key used find the related field
        """
        if not isinstance(value, int | float | str):
            raise TypeError(f"Provided value {value} is not of valid types: {type(BCSVValue)}")

        field_name: str = BCSVEntry.find_field(key)
        super().__setitem__(field_name, value)


class BCSV:
    """
    BCSV Files are table-structured format files that contain a giant header block and data entry block.
    These files remark a similar structure to modern day data tables, with one key difference
        The header block contains the definition of all field headers (columns) and field data
            Definition of these headers does not matter.
        The data block contains the table row data one line at a time. Each row is represented as a single list index,
            where a dictionary maps the key (column) to the value.
        And lastly, all strings are defined in a string table that is appended at the end of the data itself.
    BCSV Files also start with 16 bytes that are useful to explain the rest of the structure of the file.
    """
    fields: list[BCSVField]
    entries: list[BCSVEntry]


    def __init__(self, fields: list[BCSVField] = None, entries: list[BCSVEntry] = None):
        """
        Represents a given BCSV file in its enterity.

        Args:
            fields (list[BCSVFields]): One or more fields/headers within a BCSV file.
            entries (list[BCSVEntry]): One or more entries within a BCSV file.
        """

        if fields is None:
            fields = []

        if entries is None:
            entries = []

        self.verify_fields_and_entries(fields, entries)

        self.fields = fields
        self.entries = entries


    @classmethod
    def import_bcsv(cls, raw_data: BytesIO, field_names: dict[int, str] = None, str_fmt: str = STRING_FORMAT):
        """
        Takes an input stream of BCSV data and converts it into a BCSV object.

        Args:
            raw_data (BytesIO): raw stream of a file
            field_names (dict[int, str]): Contains the field_hash -> name quick lookup reference. 
                By default, a field's name is the same as the hash, this allows for human-readable names to be used instead.
            str_fmt (str): Output decoding format.
        """
        data_length: int = raw_data.seek(0, 2)
        if data_length < BCSV_HEADER_SIZE:
            raise BCSVFileError("Provided BCSV BytesIO is not in a valid format.")

        if field_names is None:
            BCSVEntry.hash_names = {}
        else:
            BCSVEntry.hash_names = field_names

        bcsv: BCSV = cls() # initialize the class with some empty entry/field lists.
        entry_count: int = fh.read_u32(raw_data, 0x0)
        field_count: int = fh.read_u32(raw_data, 0x4)
        entry_data_offset: int = fh.read_u32(raw_data, 0x8)
        entry_size_bytes: int = fh.read_u32(raw_data, 0xC)

        # Load all headers of this file
        fields_size: int = entry_data_offset - BCSV_HEADER_SIZE # BCSV Field details start after the above 16 bytes
        remainder_bytes: int = fields_size % BCSV_FIELD_SIZE
        read_field_count: int = int(fields_size / BCSV_FIELD_SIZE)
        if remainder_bytes != 0 or not read_field_count == field_count: # Make sure there is no extra space between fields and entries
            raise BCSVFileError("When trying to read the fields block of the BCSV file, field block has an "
                f"incorrect size.\nExpected field count: {field_count}\nExpected Byte count: {fields_size}\n"
                f"Remainder Bytes: {remainder_bytes}\nAmount of fields found: {read_field_count}")

        # Load all data entries / rows of this table.
        calc_data_size: int = entry_data_offset + (entry_size_bytes * entry_count)
        if calc_data_size > data_length: # Simple check, doesn't take into account the string pool
            raise BCSVFileError("When trying to read the data entries block of the BCSV file, the entry size "
                f"was incorrect.\nExpected data size: {data_length}\nCalculated data size: {calc_data_size}")

        offset: int = BCSV_HEADER_SIZE
        for _ in range(field_count):
            field_bytes: BytesIO = BytesIO(fh.read_bytes(raw_data, BCSV_FIELD_SIZE, offset))
            bcsv_field: BCSVField = BCSVField.import_field(field_bytes)
            if bcsv_field.field_hash in BCSVEntry.hash_names: # Replace hashes with field names if provided
                bcsv_field.field_name = field_names[bcsv_field.field_hash]
            bcsv.fields.append(bcsv_field)
            offset += BCSV_FIELD_SIZE

        # Read everything after the calculated data size until the end of the BCSV byte data.
        string_table_bytes: BytesIO = BytesIO(fh.read_bytes(raw_data, -1, calc_data_size))

        offset = entry_data_offset
        for _ in range(entry_count):
            bcsv_entry: BCSVEntry = BCSVEntry()
            entry_bytes: BytesIO = BytesIO(fh.read_bytes(raw_data, entry_size_bytes, offset))

            for bcsv_field in bcsv.fields:
                value: BCSVValue = bcsv_field.get_value_from_bytes(entry_bytes, str_fmt)
                if bcsv_field.field_type == BCSVType.STRING_OFFSET:
                    value = fh.read_string_until_null(string_table_bytes, value, str_fmt=str_fmt) # Read until a null byte is hit
                bcsv_entry[bcsv_field] = value
            bcsv.entries.append(bcsv_entry)
            offset += entry_size_bytes

        return bcsv


    def export_bcsv(self, str_fmt: str = STRING_FORMAT) -> BytesIO:
        """
        Converts this object back into a file stream.

        Args:
            str_fmt (str): Output decoding format.

        Returns:
            BytesIO
        """
        self.verify_fields_and_entries()

        field_count: int = len(self.fields)
        entry_count: int = len(self.entries)
        entry_data_offset: int  = BCSV_HEADER_SIZE + (BCSV_FIELD_SIZE * field_count)
        entry_size: int = self.calculate_data_entry_size()

        bcsv_data: BytesIO = BytesIO()
        fh.write_u32(bcsv_data, entry_count, 0x0)
        fh.write_u32(bcsv_data, field_count, 0x4)
        fh.write_u32(bcsv_data, entry_data_offset, 0x8)
        fh.write_u32(bcsv_data, entry_size, 0xC)

        # Write the header data back into the bcsv file
        offset = BCSV_HEADER_SIZE
        for field in self.fields:
            if not isinstance(field, BCSVField):
                raise TypeError(f"Field provided is not of type 'BCSVField'.\nReceived field type: {type(field)}\n"
                    f"Field: {field}\nField Index: {self.fields.index(field)}")
            fh.write_bytes(bcsv_data, field.export_field(), offset)
            offset += BCSV_FIELD_SIZE

        # Now write the entries back into the bcsv file
        # String pool will contain a list
        string_pool: list[StringPoolElement] = []
        for entry in self.entries:
            if not isinstance(entry, BCSVEntry):
                raise TypeError(f"Entry provided is not of type 'BCSVEntry'.\nReceived entry type: {type(entry)}\n"
                    f"Entry: {entry}\nEntry Index: {self.entries.index(entry)}")

            entry_bytes: BytesIO = BytesIO(bytearray(entry_size))
            # Loop through all fields to write into the bcsv for each entry
            for field in self.fields:
                field.set_value_in_buffer(entry_bytes, entry[field], string_pool)

            # Update the entry bytes into the BCSV data object.
            fh.write_bytes(bcsv_data, entry_bytes.getvalue(), offset)
            offset += entry_size

        # Create an empty string pool to write data to and eventually append to the end.
        string_pool_bytes: BytesIO = BytesIO()
        for pool_element in string_pool:
            fh.write_string(string_pool_bytes, pool_element.value, len(pool_element.value), offset=pool_element.offset, str_fmt=str_fmt, add_null_byte=True)

        # Add the string pool bytes into BCSV data.
        fh.write_bytes(bcsv_data, string_pool_bytes.getvalue(), offset)

        # BCSV Files are then padded with @ if their file size are not divisible by 32.
        curr_length = bcsv_data.seek(0, 2)
        if curr_length % 32 > 0:
            bcsv_data.seek(curr_length)
            fh.write_string(bcsv_data, "", 32 - (curr_length % 32), b"@", curr_length, str_fmt=str_fmt)

        return bcsv_data


    def calculate_data_entry_size(self) -> int:
        """
        Calculates the size of the entry based on the field's data type.
        Order of the entry size calculation is the following:
            STRING < FLOAT < LONG < LONG_2 < SHORT < BYTE < STRING_OFFSET
        """
        return max([field.field_offset + field.get_field_size() for field in self.fields])


    def add_bcsv_field(self, bcsv_field: BCSVField, default_value: BCSVValue):
        """
        Adds a new BCSVField and a default value to all existing data entries.
        
        Args:
            bcsv_field (BCSVField): field to add into a given file.
            default_value (BCSVValue): Default value to use for all entries.
        """
        if bcsv_field.field_hash in [field.field_hash for field in self.fields]:
            raise BCSVFileError(f"BCSVField with hash '{bcsv_field.field_hash}' already exists as a field.")

        self.fields.append(bcsv_field)
        for data_entry in self.entries:
            data_entry[bcsv_field] = default_value


    def remove_bcsv_field(self, key: BCSVKey):
        """
        Removes a new BCSVField and a default value to all existing data entries.
        
        Args:
            key (BCSVKey): field to add into a given file.
        """
        if isinstance(key, str):
            field_found: BCSVField = next((field for field in self.fields if field.field_name == key), None)
        elif isinstance(key, int):
            field_found: BCSVField = next((field for field in self.fields if field.field_hash == key), None)
        elif isinstance(key, BCSVField):
            field_found: BCSVField = next((field for field in self.fields if field == key), None)
        else:
            raise TypeError(f"Field provided is not of type '{type(BCSVKey)}.' Field Provided: {type(key)}")

        if field_found is None:
            raise ValueError(f"No BCSVField was found with key: {key}")

        for entry in self.entries:
            del entry[key]

        self.fields.remove(field_found)

    def add_bcsv_entry(self, bcsv_entry: BCSVEntry):
        """
        Adds a new data entry using field names or hashes as keys with complete field validation.
        
        Args:
            bcsv_entry (BCSVEntry): entry to add into the BCSV
        """
        if not self.fields:
            raise KeyError("Cannot add a BCSVEntry to a BCSV with no defined fields.")
        elif bcsv_entry is None or len(bcsv_entry.keys()) == 0:
            raise ValueError("Cannot add an empty BCSVEntry to the BCSV.")

        self.entries.append(bcsv_entry)


    def remove_bcsv_entry(self, bcsv_entry: int | BCSVEntry):
        """
        Deletes a BCSVEntry by either the Entry itself or the index number.
        
        Args:
            bcsv_entry (int | BCSVEntry): entry (or index) to remove from the BCSV
        """
        if isinstance(bcsv_entry, int):
            entry: BCSVEntry = self.entries[bcsv_entry]
        elif isinstance(bcsv_entry, BCSVEntry):
            entry: BCSVEntry = bcsv_entry
        else:
            raise ValueError(f"Cannot index BCSVEntry with value of type {type(bcsv_entry)}")

        self.entries.remove(entry)

    def verify_fields_and_entries(self, fields: list[BCSVField] = None, entries: list[BCSVEntry] = None):
        """
        Verifies if all the BCSV Fields are in fact properly defined keys/fields. Similarly validates entries.

        Args:
            fields (list[BCSVField]): A list of headers/fields for a BCSV file
            entries (list[BCSVEntry]): A list of rows/entries for a BCSV file
        """

        if fields is None:
            fields = self.fields
        
        if entries is None:
            entries = self.entries

        for bcsv_field in fields:
            if not isinstance(bcsv_field, BCSVField):
                raise BCSVFileError(f"Fields provided is not of type 'BCSVField'.\nReceived field type: {type(bcsv_field)}")
            
        for bcsv_entry in entries:
            if not isinstance(bcsv_entry, BCSVEntry):
                raise BCSVFileError(f"Entries provided is not of type 'BCSVEntry'.\nReceived field type: {type(bcsv_entry)}")
            
