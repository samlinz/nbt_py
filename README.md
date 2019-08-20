# nbt_py

Python library which allows you to load, filter, modify and save NBT binary files
using Python and its datatypes.

NBT or *Named Binary Tag* is proprietary data format used by *Minecraft* to store
its data. It can be quite difficult to work with and this tool simplifies that process.

### Features

* Load and parse compressed or uncompressed NBT binary files
* Flatten the nested structure into a Python dictionary
* Search tags using tag keys, types and/or names of their ancestors
* Modify the values as standard Python objects
* Save the NBTTag objects as compressed or uncompressed binary files

### Key functions

Check docstrings and examples for how to use.

```
nbt_py.fileio.load_and_parse_nbt_file
nbt_py.fileio.save_nbt_file
nbt_py.filter.find_tags
nbt_py.filter.get_lookup
nbt_py.util.is_gzipped
nbt_py.util.nbt_to_dict
```

NBT tags are represented as NBTTag objects which have following properties:
```
name -> Name of the tag
type -> Type of the tag as TagTypes enumeration
parent -> Reference to the parent of the tag, None for root
payload -> Value of the tag
```

### Example

Loading *level.dat*, modifying a specific nested tag and overriding original.

```python
import nbt_py.filter
import nbt_py.fileio

# Load NBT file.
parsed = nbt_py.fileio.load_and_parse_nbt_file('level.dat')

# Find a specific tag and modify its value (payload).
raining_tag = nbt_py.filter.find_tags(parsed, name_like='raining')[0]
raining_tag.payload = 1

# Save the modified NBT file over the original file.
nbt_py.fileio.save_nbt_file(parsed
                            , 'level.dat'
                            , override=True)
```