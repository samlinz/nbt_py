from enum import Enum

# Endianess of binary values.
ENDIANESS = 'big'

# Value used for empty values.
EMPTY_NAME = None

# Separator in fully qualified names.
FULLY_QUALIFIED_SEPARATOR = '_'


class TagTypes(Enum):
    """
    Enumeration containing all the available tag types in NBT format.
    """

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
    TagTypes.TAG_End       : -1,
    TagTypes.TAG_Byte      : 1,
    TagTypes.TAG_Short     : 2,
    TagTypes.TAG_Int       : 4,
    TagTypes.TAG_Long      : 8,
    TagTypes.TAG_Float     : 4,
    TagTypes.TAG_Double    : 8,
    TagTypes.TAG_Byte_Array: 0,
    TagTypes.TAG_String    : 0,
    TagTypes.TAG_List      : 0,
    TagTypes.TAG_Compound  : 0,
    TagTypes.TAG_Int_Array : 0,
    TagTypes.TAG_Long_Array: 0,
}

# Integer types in the format, all represented as int in Python, different byte lengths in binary.
INTEGER_TYPES = [TagTypes.TAG_Byte
    , TagTypes.TAG_Short
    , TagTypes.TAG_Int
    , TagTypes.TAG_Long]

# List types.
LIST_TYPES = [TagTypes.TAG_List, TagTypes.TAG_Int_Array, TagTypes.TAG_Long_Array]


class NBTTag:
    """
    Class representing a full NBT tag with name, type and child hierarchy.
    Might or might not be the root node, root node has None as parent and None as name.
    Returned by parsing functions.
    """

    def __init__(self):
        self.type = None
        self.name = None
        self.payload = None
        self.parent = None
        self.list_type = None

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
