from nbt_py.core import FULLY_QUALIFIED_SEPARATOR, TagTypes
from nbt_py.util import __get_full_qualified_name


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
