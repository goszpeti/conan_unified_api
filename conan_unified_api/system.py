""" OS Abstraction Layer for all file based functions """

import os
import stat
from pathlib import Path

from conan_unified_api.logger import Logger

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
