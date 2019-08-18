import struct
import gzip
from enum import Enum

FILE = 'level.dat'

ENDIANESS = 'big'
EMPTY_NAME = None

# Reference: https://minecraft.gamepedia.com/NBT_format

class TagTypes(Enum):
    TAG_End = 0
    TAG_Byte = 1
    TAG_Short = 2
    TAG_Int = 3
    TAG_Long = 4
    TAG_Float = 5
    TAG_Double = 6
    TAG_Byte_Array = 7
    TAG_String = 8
    TAG_List = 9
    TAG_Compound = 10
    TAG_Int_Array = 11
    TAG_Long_Array = 12

# Lengths of types in bytes, 0 indicates that type has no fixed length.
TAG_TYPE_BYTE_LENGTHS = {
    TagTypes.TAG_End: -1,
    TagTypes.TAG_Byte : 1,
    TagTypes.TAG_Short : 2,
    TagTypes.TAG_Int : 4,
    TagTypes.TAG_Long : 8,
    TagTypes.TAG_Float : 4,
    TagTypes.TAG_Double : 8,
    TagTypes.TAG_Byte_Array : 0,
    TagTypes.TAG_String : 0,
    TagTypes.TAG_List : 0,
    TagTypes.TAG_Compound : 0,
    TagTypes.TAG_Int_Array : 0,
    TagTypes.TAG_Long_Array : 0,
}

def __read_nbt_string(file):
    # Read the length of the string.
    length = file.read(2)
    length, = struct.unpack('>H', length)

    if length == 0:
        return EMPTY_NAME

    # Read the string
    str = file.read(length)
    str, = struct.unpack(f'>{length}s', str)
    str = str.decode('utf-8')

    return str

def __read_int(file, byte_length, signed=True):
    data = file.read(byte_length)
    return int.from_bytes(data, ENDIANESS, signed=signed)

def __handle_tag_payload(file, tag_type):
    if tag_type == TagTypes.TAG_End:
        raise ValueError(f'Found TAG_End at offset {file.offset}')

    integer_types = [TagTypes.TAG_Byte
                       , TagTypes.TAG_Short
                       , TagTypes.TAG_Int
                       , TagTypes.TAG_Long]

    list_types = [TagTypes.TAG_List, TagTypes.TAG_Int_Array, TagTypes.TAG_Long_Array]

    # Tag is some N-bit integer type.
    if tag_type in integer_types:
        return __read_int(file, TAG_TYPE_BYTE_LENGTHS[tag_type])

    # Tag is 32bit signed float.
    if tag_type == TagTypes.TAG_Float:
        data = file.read(TAG_TYPE_BYTE_LENGTHS[tag_type])
        data, = struct.unpack('>f', data)
        return data

    # Tag is 64bit signed float.
    if tag_type == TagTypes.TAG_Double:
        data = file.read(TAG_TYPE_BYTE_LENGTHS[tag_type])
        data, = struct.unpack('>d', data)
        return data

    # Tag is byte array.
    if tag_type == TagTypes.TAG_Byte_Array:
        size = __read_int(file, 4)
        data, = file.read(size)
        return data

    # Tag is UTF-8 string.
    if tag_type == TagTypes.TAG_String:
        return __read_nbt_string(file)

    # Tag is some of the list types.
    if tag_type in list_types:
        if tag_type == TagTypes.TAG_List:
            list_tag_type = __read_int(file, 1)
            list_tag_type = TagTypes(list_tag_type)
        elif tag_type == TagTypes.TAG_Int_Array:
            list_tag_type = TagTypes.TAG_Int
        elif tag_type == TagTypes.TAG_Long_Array:
            list_tag_type = TagTypes.TAG_Long
        else:
            raise ValueError(f'Invalid list type {tag_type} at offset {file.offset}')

        list_length = __read_int(file, 4)
        items = []

        # List of type TAG_End indicates an empty list.
        if list_tag_type == TagTypes.TAG_End:
            return items

        # Parse the members of the list.
        for i in range(list_length):
            item = __handle_tag_payload(file, list_tag_type)
            items.append(item)

        return items

    if tag_type == TagTypes.TAG_Compound:
        get_next = True
        children = []

        while get_next:
            child = __parse_tag(file)
            if child['type'] == TagTypes.TAG_End:
                # Stop getting children for compound type.
                get_next = False
            else:
                # Add parsed child to compound type.
                children.append(child)

        # Add children as dictionary payload to compound tag.
        compound_payload = {child['name']: child['payload'] for child in children}
        return compound_payload


def __parse_tag_content(tag_type, file):
    # End tag does not contain name.
    if tag_type == TagTypes.TAG_End:
        tag_name = EMPTY_NAME
        payload = None
    else:
        tag_name = __read_nbt_string(file)
        # Recursive call.
        payload = __handle_tag_payload(file, tag_type)

    result = dict()
    result['type'] = tag_type
    result['name'] = tag_name
    result['payload'] = payload

    return result

def __parse_tag(file):
    # Read and parse tag type into enum member.
    byte_tag_type = __read_int(file, 1)
    tag_type = TagTypes(byte_tag_type)

    return __parse_tag_content(tag_type, file)

def parse_file(file) -> dict:
    parsed_root = __parse_tag(file)
    return parsed_root['payload']

def load_and_parse_file(filepath : str) -> dict:
    # NBT files might or might not be GZIP compressed, so only way to know is to try.
    try:
        with gzip.open(filepath, 'rb') as f:
            return parse_file(f)
    except OSError:
        # Not a gzipped file.
        with open(filepath, 'rb') as f:
            return parse_file(f)

parsed = load_and_parse_file(FILE)

print('Done')