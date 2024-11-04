"""OS Abstraction Layer for all file based functions"""

import os
import stat
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Dict, List

from conan_unified_api.base.logger import Logger


def str2bool(value: str) -> bool:
    """Own impl. isntead of distutils.util.strtobool
    because distutils will be deprecated"""
    value = value.lower()
    if value in {"yes", "true", "y", "1"}:
        return True
    if value in {"no", "false", "n", "0"}:
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
        value_str = str(value)
        # this is not really safe, but there can be wild values...
        if "any" in value_str.lower() or "none" in value_str.lower():
            continue
        res_list.append(name + "=" + value_str)
    return res_list


def delete_path(dst: Path) -> None:
    """
    Delete file or (non-empty) folder recursively.
    Exceptions will be caught and message logged to stdout.
    """
    from shutil import rmtree

    try:
        if dst.is_file():
            dst.unlink()
        elif dst.is_dir():

            def rm_dir_readonly(func: Callable, path: str, _) -> None:
                "Clear the readonly bit and reattempt the removal"
                os.chmod(path, stat.S_IWRITE)  # noqa: PTH101
                func(path)

            rmtree(str(dst), onerror=rm_dir_readonly)  # onexc only usable from 3.12
    except Exception as e:
        Logger().warning("Can't delete %s: %s", str(dst), str(e))


@contextmanager
def save_sys_path():  # noqa: ANN201
    saved_path = sys.path.copy()
    yield
    # restore
    sys.path = saved_path
