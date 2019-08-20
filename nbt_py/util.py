from typing import Dict, Any

from nbt_py.core import NBTTag, TagTypes, FULLY_QUALIFIED_SEPARATOR


def is_gzipped(filepath: str) -> bool:
    """
    Check if the file at given path is gzip encoded.
    :param filepath: File path to check.
    :return: True if file is compressed with GZIP.
    """

    MAGIC_NUMBER = '1f8b'
    with open(filepath, 'rb') as f:
        first_two_bytes = f.read(2).hex()
    return first_two_bytes == MAGIC_NUMBER


def nbt_to_dict(nbt_tag: NBTTag) -> Dict[str, Any]:
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


def _get_full_qualified_name(nb_tag: NBTTag, separator: str = FULLY_QUALIFIED_SEPARATOR) -> str:
    """
    Get a fully qualified name for an NBT tag. It will include all parents' names separated
    with underscore except the root tag.

    :param nb_tag: Tag for which the name will be constructed.
    :return: Fully qualified name as string.
    """

    current_tag = nb_tag
    name = current_tag.name
    while current_tag.parent and current_tag.parent.name:
        name = f'{current_tag.parent.name}{separator}{name}'
        current_tag = current_tag.parent

    return name
