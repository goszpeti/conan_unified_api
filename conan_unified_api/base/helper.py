""" OS Abstraction Layer for all file based functions """

import os
import stat
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List

from conan_unified_api.base.logger import Logger


def str2bool(value: str) -> bool:
    """ Own impl. isntead of distutils.util.strtobool
      because distutils will be deprecated """
    value = value.lower()
    if value in {'yes', 'true', 'y', '1'}:
        return True
    if value in {'no', 'false', 'n', '0'}:
        return False
    return False


def create_key_value_pair_list(input_dict: Dict[str, Any]) -> List[str]:
    """
    Helper to create name=value string list from dict
    Filters "ANY" options.
    """
    res_list: List[str] = []
    if not input_dict:
        return res_list
    for name, value in input_dict.items():
        value = str(value)
        # this is not really safe, but there can be wild values...
        if "any" in value.lower() or "none" in value.lower():
            continue
        res_list.append(name + "=" + value)
    return res_list

def delete_path(dst: Path):
    """
    Delete file or (non-empty) folder recursively.
    Exceptions will be caught and message logged to stdout.
    """
    from shutil import rmtree
    try:
        if dst.is_file():
            os.remove(dst)
        elif dst.is_dir():
            def rm_dir_readonly(func, path, _):
                "Clear the readonly bit and reattempt the removal"
                os.chmod(path, stat.S_IWRITE)
                func(path)
            rmtree(str(dst), onerror=rm_dir_readonly)
    except Exception as e:
        Logger().warning(f"Can't delete {str(dst)}: {str(e)}")


@contextmanager
def save_sys_path():

    saved_path = sys.path.copy()
    yield
    # restore
    sys.path = saved_path
