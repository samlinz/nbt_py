import os
import struct
import gzip
from enum import Enum

# Reference: https://minecraft.gamepedia.com/NBT_format

FILE = 'level.dat'

ENDIANESS = 'big'
EMPTY_NAME = None
ROOT_NAME = None
FULLY_QUALIFIED_SEPARATOR = '_'

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

INTEGER_TYPES = [TagTypes.TAG_Byte
                       , TagTypes.TAG_Short
                       , TagTypes.TAG_Int
                       , TagTypes.TAG_Long]

LIST_TYPES = [TagTypes.TAG_List, TagTypes.TAG_Int_Array, TagTypes.TAG_Long_Array]

class NBTTag:
    def __init__(self):
        self.type = None
        self.name = None
        self.payload = None
        self.parent = None
        self.list_type = None

    def find_children(self, name, type):
        pass

    def find_child(self, name, type, throw_on_duplicate=False):
        pass

    @staticmethod
    def create(type, name, payload, parent=None):
        tag = NBTTag()
        tag.type = type
        tag.name = name
        tag.payload = payload
        tag.parent = parent

        return tag

    def __repr__(self) -> str:
        return f'{self.name}: {self.payload}'

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

def __write_nbt_string(file, str):
    # Write string length.
    length = len(str) if str else 0
    __write_int(file, length, 2)

    if length == 0:
        return

    # Read the string
    str = struct.pack(f'>{length}s', str.encode('utf-8'))
    file.write(str)

    return str

def __read_int(file, byte_length, signed=True):
    data = file.read(byte_length)
    return int.from_bytes(data, ENDIANESS, signed=signed)

def __write_int(file, value : int, byte_length, *, signed=True):
    int_bytes = value.to_bytes(byte_length, ENDIANESS, signed=signed)
    file.write(int_bytes)

def __handle_tag_payload(file, tag_type):
    if tag_type == TagTypes.TAG_End:
        raise ValueError(f'Found TAG_End at offset {file.offset}')

    # Tag is some N-bit integer type.
    if tag_type in INTEGER_TYPES:
        value = __read_int(file, TAG_TYPE_BYTE_LENGTHS[tag_type])
        return value, None

    # Tag is 32bit signed float.
    if tag_type == TagTypes.TAG_Float:
        data = file.read(TAG_TYPE_BYTE_LENGTHS[tag_type])
        data, = struct.unpack('>f', data)
        return data, None

    # Tag is 64bit signed float.
    if tag_type == TagTypes.TAG_Double:
        data = file.read(TAG_TYPE_BYTE_LENGTHS[tag_type])
        data, = struct.unpack('>d', data)
        return data, None

    # Tag is byte array.
    if tag_type == TagTypes.TAG_Byte_Array:
        size = __read_int(file, 4)
        data, = file.read(size)
        return data, None

    # Tag is UTF-8 string.
    if tag_type == TagTypes.TAG_String:
        value = __read_nbt_string(file)
        return value, None

    # Tag is some of the list types.
    if tag_type in LIST_TYPES:
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
            return items, None

        # Parse the members of the list.
        for i in range(list_length):
            item, _ = __handle_tag_payload(file, list_tag_type)
            items.append(item)

        return items, list_tag_type

    if tag_type == TagTypes.TAG_Compound:
        get_next = True
        children = []

        while get_next:
            child = __parse_tag(file)
            if child.type == TagTypes.TAG_End:
                # Stop getting children for compound type.
                get_next = False
            else:
                # Add parsed child to compound type.
                children.append(child)

        # Add children as dictionary payload to compound tag.
        return children, None


def __parse_tag_content(tag_type, file):
    # End tag does not contain name.
    list_type = None

    if tag_type == TagTypes.TAG_End:
        tag_name = EMPTY_NAME
        payload = None
    else:
        tag_name = __read_nbt_string(file)
        # Recursive call.
        payload, list_type = __handle_tag_payload(file, tag_type)

    result = NBTTag.create(tag_type, tag_name, payload)
    if tag_type == TagTypes.TAG_List:
        result.list_type = list_type

    # Set parent reference to all children.
    if tag_type == TagTypes.TAG_Compound:
        for child in result.payload:
            child.parent = result

    return result

def __parse_tag(file):
    # Read and parse tag type into enum member.
    byte_tag_type = __read_int(file, 1)
    tag_type = TagTypes(byte_tag_type)

    return __parse_tag_content(tag_type, file)

def parse_file(file) -> NBTTag:
    parsed_root = __parse_tag(file)
    parsed_root.name = ROOT_NAME
    return parsed_root

def load_and_parse_nbt_file(filepath : str, *, return_gzipped=False):
    """
    Load a compressed or uncompressed NBT file and parse it into NBTTag object.

    :param filepath: Path to file.
    :return: NBTTag for the root tag and the whole nested structure as children.
    """

    # NBT files might or might not be GZIP compressed, so only way to know is to try.

    if not os.path.exists(filepath):
       raise ValueError(f'File {filepath} does not exits!')

    gzipped = is_gzipped(filepath)

    if gzipped:
        file = gzip.open(filepath, 'rb')
    else:
        file = open(filepath, 'rb')

    with file:
        result = parse_file(file)

    return (result, gzipped) if return_gzipped else result

def __get_full_qualified_name(nb_tag):
    """
    Get a fully qualified name for an NBT tag. It will include all parents' names separated
    with underscore except the root tag.

    :param nb_tag: Tag for which the name will be constructed.
    :return: Fully qualified name as string.
    """

    current_tag = nb_tag
    name = current_tag.name
    while current_tag.parent and current_tag.parent.name:
        name = f'{current_tag.parent.name}{FULLY_QUALIFIED_SEPARATOR}{name}'
        current_tag = current_tag.parent

    return name


def get_lookup(nbt_tag, *, all_fully_qualified=False):
    """
    Get a flattened lookup dictionary of the whole nested NBT tag structure.
    Tag names will be the keys and NBTTag objects the values.

    In case of duplicate keys the fully qualified names which contain all the parent tags' names
    separated with underscore will be used to make them unique.

    :param nbt_tag: Tag from which the recursive flattening will begin.
    :param all_fully_qualified: If true fully qualified name will be used for all tags.
    :return: Single-deep Python dictionary which has tag names as keys and objects as values.
    """

    result = dict()

    name = nbt_tag.name
    type = nbt_tag.type
    payload = nbt_tag.payload

    if name:
        if all_fully_qualified:
            name = __get_full_qualified_name(nbt_tag)
        result[name] = nbt_tag

    if type == TagTypes.TAG_Compound:
        for child in payload:
            child_dict = get_lookup(child, all_fully_qualified=all_fully_qualified)
            for child_key, child_value in child_dict.items():
                if child_key in result:
                    if all_fully_qualified:
                        raise ValueError(
                            f'Duplicate fully qualified name {child_key}')
                    existing_duplicate = result.pop(child_key)
                    result[__get_full_qualified_name(existing_duplicate)] = existing_duplicate
                    result[__get_full_qualified_name(child_value)] = child_value
                else:
                    result[child_key] = child_value

    return result


def nbt_to_dict(nbt_tag : NBTTag):
    """
    Convert NBT tag into python dictionary.
    All NBT compound types will be transformed into nested Python dictionaries.

    :param nbt_tag: NBTTag object which will be the root object of the dict, must be compound type.
    :return: Python dictionary which will have tag names as keys and payloads as values.
    """
    result = dict()

    for member in nbt_tag.payload:
        is_compound = member.type == TagTypes.TAG_Compound
        result[member.name] = nbt_to_dict(member) if is_compound else member.payload

    return result

def find_tags(nbt_tag, *, name_like=None, parents_like=None, types=None, case_insensitive=True):
    """
    Find tags using several filters.
    :param nbt_tag: Tag from which the search will begin.
    :param name_like: String which will be matched against the key name.
    :param parents_like: String which will be matched against all parents' names.
    :param types: List of types that will be matched.
    :param case_insensitive: If true the key and search strings will be case insensitive.
    :return: List of tags that match the given filters.
    """

    # Create a lookup table with fully qualified names.
    lookup = get_lookup(nbt_tag, all_fully_qualified=True)
    # Filter results list.
    result = []

    for key, value in lookup.items():
        key_name = key.lower() if case_insensitive else key
        parents_name = None

        # Split fully qualified name into parents and the actual name part.
        if FULLY_QUALIFIED_SEPARATOR in key_name:
            name_parts = key_name.split(FULLY_QUALIFIED_SEPARATOR)
            key_name = name_parts[-1]
            if len(name_parts) > 1:
                parents_name = name_parts[:-1]

        # Match tag name.
        if name_like:
            name_like = name_like.lower() if case_insensitive else name_like
            if name_like in key_name:
                result.append(value)
                continue

        # Match tag parents' names.
        if parents_like and parents_name:
            parents_like = parents_like.lower() if case_insensitive else parents_like
            if parents_like in parents_name:
                result.append(value)
                continue

        # Match types.
        if types:
            tag_type = value.type
            if tag_type in types:
                result.append(value)
                continue

    return result

def __write_tag_payload(file, nbt_tag):
    tag_type = nbt_tag.type
    payload = nbt_tag.payload

    # Write tag payload.
    if tag_type in INTEGER_TYPES:
        __write_int(file
                    , payload
                    , TAG_TYPE_BYTE_LENGTHS[tag_type])
        return

    if tag_type == TagTypes.TAG_Float:
        data = struct.pack('>f', payload)
        file.write(data)
        return

    if tag_type == TagTypes.TAG_Double:
        data = struct.pack('>d', payload)
        file.write(data)
        return

    if tag_type == TagTypes.TAG_Byte_Array:
        __write_int(file, len(payload), 4)

        for value in payload:
            byte_value = value.to_bytes(1, ENDIANESS, signed=True)
            file.write(byte_value)

        return

    # Tag is UTF-8 string.
    if tag_type == TagTypes.TAG_String:
        __write_nbt_string(file, payload)
        return

    # Tag is some of the list types.
    if tag_type in LIST_TYPES:
        if tag_type == TagTypes.TAG_List:
            list_tag_type = nbt_tag.list_type

            if list_tag_type == None:
                # Empty list, type is TAG_End.
                __write_int(file, TagTypes.TAG_End.value, 1)
                return

            # Write the type of list members.
            __write_int(file, list_tag_type.value, 1)
        elif tag_type == TagTypes.TAG_Int_Array:
            list_tag_type = TagTypes.TAG_Int
        elif tag_type == TagTypes.TAG_Long_Array:
            list_tag_type = TagTypes.TAG_Long
        else:
            raise ValueError(f'Invalid list tag type {tag_type}')

        # Write the members of the list iteratively.
        for item in payload:
            child_tag = NBTTag.create(list_tag_type, None, item)
            __write_tag_payload(file, child_tag)

        return

    if tag_type == TagTypes.TAG_Compound:
        for child in payload:
            __write_tag(file, child)

        return

def __write_tag_content(file, nbt_tag):
    tag_type = nbt_tag.type

    if tag_type == TagTypes.TAG_End:
        return

    # Write tag name.
    __write_nbt_string(file, nbt_tag.name)

    __write_tag_payload(file, nbt_tag)


def __write_tag(file, nbt_tag):
    # Write tag type, single byte.
    tag_type_int = nbt_tag.type.value
    __write_int(file, tag_type_int, 1)

    # Write tag name.
    name = nbt_tag.name
    __write_nbt_string(file, name)

    # Write tag payload.
    __write_tag_payload(file, nbt_tag)

def __get_backup_filepath(base):
    number = 0
    filepath = None
    continue_search = True
    while continue_search:
        filepath = f'{base}{number if number > 0 else ""}'
        if os.path.exists(filepath):
            continue_search = True
            number += 1
        else:
            continue_search = False

    return filepath

def save_nbt_file(nbt_tag, filepath : str, *, gzipped=True, override=False, create_backup=True):
    if not override and os.path.exists(filepath):
        raise ValueError(f'File {filepath} exists already')

    backup_created = None
    if override and os.path.exists(filepath):
        if create_backup:
            # Rename the original file and remove it if everything goes ok.
            backup_created = __get_backup_filepath(f'{filepath}.bak')
            os.rename(filepath, backup_created)
        else:
            # Remove the old file before writing new.
            os.remove(filepath)
    try:
        if gzipped:
            file = gzip.open(filepath, mode='wb')
        else:
            file = open(filepath, mode='wb')

        with file:
            __write_tag(file, nbt_tag)
    except Exception as e:
        # Remove invalid file.
        if os.path.exists(filepath):
            os.remove(filepath)

        # Revert from backup.
        if backup_created:
            os.rename(backup_created, filepath)

        raise e
    else:
        # Remove backup if everything went well.
        if backup_created:
            os.remove(backup_created)


def is_gzipped(filepath):
    MAGIC_NUMBER = '1f8b'
    with open(filepath, 'rb') as f:
        first_two_bytes = f.read(2).hex()
    return first_two_bytes == MAGIC_NUMBER

gzipped = is_gzipped(FILE)
parsed = load_and_parse_nbt_file(FILE)
asd = find_tags(parsed, name_like='raining')[0]
asd.payload = 1
save_nbt_file(parsed, 'sibale.sav', override=True)
parsed2 = load_and_parse_nbt_file(FILE)
parsed3 = load_and_parse_nbt_file('sibale.sav')

print('Done')