import os
import struct
import gzip
from enum import Enum

# Reference: https://minecraft.gamepedia.com/NBT_format
from nbt_py.fileio import load_and_parse_nbt_file, save_nbt_file
from nbt_py.filter import find_tags
from nbt_py.util import is_gzipped

FILE = 'level.dat'


gzipped = is_gzipped(FILE)
parsed = load_and_parse_nbt_file(FILE)
asd = find_tags(parsed, name_like='raining')[0]
asd.payload = 1
save_nbt_file(parsed, 'sibale.sav', override=True)
parsed2 = load_and_parse_nbt_file(FILE)
parsed3 = load_and_parse_nbt_file('sibale.sav')

print('Done')