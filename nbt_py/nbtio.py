import struct
from typing import Tuple, Optional, Any

from nbt_py.core import TagTypes, EMPTY_NAME, NBTTag, INTEGER_TYPES, \
    TAG_TYPE_BYTE_LENGTHS, ENDIANESS, LIST_TYPES


def __read_nbt_string(file) -> str:
    """
    Read a string from open NBT file.
    Strings have their length first, then the UTF-8 encoded binary string.
    :param file: Open file pointer to correct position.
    :return: Python string in UTF-8 format.
    """

    # Read the length of the string.
    length = file.read(2)
    length, = struct.unpack('>H', length)

    # Empty strings have no content.
    if length == 0:
        return EMPTY_NAME

    # Read the string
    str = file.read(length)
    str, = struct.unpack(f'>{length}s', str)

    # Decode binary string.
    str = str.decode('utf-8')

    return str


def __write_nbt_string(file, str: str) -> None:
    """
    Write Python string into NBT binary format.
    :param file: Open file pointer.
    :param str: String to be encoded encoded and written.
    """

    # Write string length.
    length = len(str) if str else 0
    __write_nbt_int(file, length, 2)

    if length == 0:
        return

    # Encode and write the binary string.
    str = struct.pack(f'>{length}s', str.encode('utf-8'))
    file.write(str)


def __read_nbt_int(file, byte_length: int, signed: bool = True) -> int:
    """
    Read N-byte integer value from NBT file.

    :param file: Open file pointer.
    :param byte_length: Length of the integer value in bytes.
    :param signed: If true then use signed integer format.
    :return: The encoded integer as Python integer.
    """
    data = file.read(byte_length)
    return int.from_bytes(data, ENDIANESS, signed=signed)


def __write_nbt_int(file, value: int, byte_length: int, *, signed: bool = True) -> None:
    """
    Write Python integer value into NBT binary format.
    :param file: Open file pointer.
    :param value: Python integer value.
    :param byte_length: Byte length of the target binary encoding.
    :param signed: If true write as signed format.
    """
    int_bytes = value.to_bytes(byte_length, ENDIANESS, signed=signed)
    file.write(int_bytes)


def __read_tag_payload(file, tag_type: TagTypes) -> Tuple[Any, Optional[TagTypes]]:
    """
    Read NBT tag's payload, knowing the type.
    :param file: Open file pointer.
    :param tag_type: Tag's NBT type.
    :return: Tuple with first value being the corresponding Python value and second list item
    type if
            value was list.
    """
    if tag_type == TagTypes.TAG_End:
        raise ValueError(f'Found TAG_End at offset {file.offset}')

    # Tag is some N-bit integer type.
    if tag_type in INTEGER_TYPES:
        value = __read_nbt_int(file, TAG_TYPE_BYTE_LENGTHS[tag_type])
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
        size = __read_nbt_int(file, 4)
        data, = file.read(size)
        return data, None

    # Tag is UTF-8 string.
    if tag_type == TagTypes.TAG_String:
        value = __read_nbt_string(file)
        return value, None

    # Tag is some of the list types.
    if tag_type in LIST_TYPES:
        if tag_type == TagTypes.TAG_List:
            list_tag_type = __read_nbt_int(file, 1)
            list_tag_type = TagTypes(list_tag_type)
        elif tag_type == TagTypes.TAG_Int_Array:
            list_tag_type = TagTypes.TAG_Int
        elif tag_type == TagTypes.TAG_Long_Array:
            list_tag_type = TagTypes.TAG_Long
        else:
            raise ValueError(f'Invalid list type {tag_type} at offset {file.offset}')

        list_length = __read_nbt_int(file, 4)
        items = []

        # List of type TAG_End indicates an empty list.
        if list_tag_type == TagTypes.TAG_End:
            return items, None

        # Parse the members of the list.
        for i in range(list_length):
            item, _ = __read_tag_payload(file, list_tag_type)
            items.append(item)

        return items, list_tag_type

    # Tag is nested compound type.
    if tag_type == TagTypes.TAG_Compound:
        get_next = True
        children = []

        while get_next:
            child = _read_tag(file)
            if child.type == TagTypes.TAG_End:
                # Stop getting children for compound type.
                get_next = False
            else:
                # Add parsed child to compound type.
                children.append(child)

        # Add children as dictionary payload to compound tag.
        return children, None


def __parse_tag_content(file, tag_type: TagTypes) -> NBTTag:
    """
    Read and parse tag's (nested) content and return a representative
    NBTTag object.
    :param file: Open file pointer.
    :param tag_type: Tag's type.
    :return: NBTTag object representing the metadata and payload.
    """

    # End tag does not contain name.
    list_type = None

    if tag_type == TagTypes.TAG_End:
        tag_name = EMPTY_NAME
        payload = None
    else:
        tag_name = __read_nbt_string(file)
        # Recursive call.
        payload, list_type = __read_tag_payload(file, tag_type)

    result = NBTTag.create(tag_type, tag_name, payload)
    if tag_type == TagTypes.TAG_List:
        result.list_type = list_type

    # Set parent reference to all children.
    if tag_type == TagTypes.TAG_Compound:
        for child in result.payload:
            child.parent = result

    return result


def __write_tag_payload(file, nbt_tag: NBTTag) -> None:
    """
    Write tag's payload.
    :param file: Open file pointer.
    :param nbt_tag: NBT tag object which' payload will be written.
    """
    tag_type = nbt_tag.type
    payload = nbt_tag.payload

    # Write tag payload.
    if tag_type in INTEGER_TYPES:
        __write_nbt_int(file
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
        __write_nbt_int(file, len(payload), 4)

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
                __write_nbt_int(file, TagTypes.TAG_End.value, 1)
                return

            # Write the type of list members.
            __write_nbt_int(file, list_tag_type.value, 1)
        elif tag_type == TagTypes.TAG_Int_Array:
            list_tag_type = TagTypes.TAG_Int
        elif tag_type == TagTypes.TAG_Long_Array:
            list_tag_type = TagTypes.TAG_Long
        else:
            raise ValueError(f'Invalid list tag type {tag_type}')

        # Write list length.
        __write_nbt_int(file, len(payload), 4)

        # Write the members of the list iteratively.
        for item in payload:
            child_tag = NBTTag.create(list_tag_type, None, item)
            __write_tag_payload(file, child_tag)

        return

    if tag_type == TagTypes.TAG_Compound:
        for child in payload:
            _write_tag(file, child)

        # Write compound ending tag.
        _write_tag(file, NBTTag.create(TagTypes.TAG_End, None, None))

        return


def _read_tag(file) -> NBTTag:
    """
    Parse a tag at the open file pointer's location, return NBTTag object.
    :param file: Open file pointer pointing to the starting location of a new tag.
    :return: NBTTag object.
    """

    # Read and parse tag type into enum member.
    byte_tag_type = __read_nbt_int(file, 1)
    tag_type = TagTypes(byte_tag_type)

    return __parse_tag_content(file, tag_type)


def _write_tag(file, nbt_tag: NBTTag) -> None:
    """
    Write NBTTag into the open file pointer.
    :param file: Open file pointer.
    :param nbt_tag: Tag to write.
    """

    # Write tag type, single byte.
    tag_type_int = nbt_tag.type.value
    __write_nbt_int(file, tag_type_int, 1)

    # Write tag name.
    __write_nbt_string(file, nbt_tag.name)

    # Write tag payload.
    __write_tag_payload(file, nbt_tag)
