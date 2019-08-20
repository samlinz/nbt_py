import gzip
import os

from nbt_py.nbtio import __write_tag, parse_file
from nbt_py.util import is_gzipped


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