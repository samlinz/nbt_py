import gzip
import os

from nbt_py.nbtio import __write_tag, __parse_tag
from nbt_py.util import is_gzipped


def __get_backup_filepath(base):
    """
    Find an unused name for the backup file.
    :param base: Base name for the backup files.
    :return: Filepath that does not exists, for the backup file.
    """

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


def save_nbt_file(nbt_tag, filepath: str, *, gzipped=True, override=False, create_backup=True):
    """
    Save the NBT tag into file in binary format.
    Preferably the tag loaded with loading functions and modified with relevant functions.

    :param nbt_tag: The tag that will be the root of structure saved into file.
    :param filepath: Target file path.
    :param gzipped: If true use gzip compression.
    :param override: If true override existing value.
    :param create_backup: If true and override is true, create temporary backup for the original
    file.
    """
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


def load_and_parse_nbt_file(filepath: str, *, return_gzipped=False):
    """
    Load a compressed or uncompressed NBT file and parse it into NBTTag object.

    :param filepath: Path to file.
    :return: NBTTag for the root tag and the whole nested structure as children.
    """

    if not os.path.exists(filepath):
        raise ValueError(f'File {filepath} does not exits!')

    # Find out if the file is compressed.
    gzipped = is_gzipped(filepath)

    if gzipped:
        file = gzip.open(filepath, 'rb')
    else:
        file = open(filepath, 'rb')

    # Parse the file into NBTTag.
    with file:
        result = __parse_tag(file)

    return (result, gzipped) if return_gzipped else result
