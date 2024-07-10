""" OS Abstraction Layer for all file based functions """

from importlib.metadata import distribution
from packaging.version import Version
import os
import stat
from pathlib import Path
import sys

from conan_unified_api.logger import Logger
from contextlib import contextmanager

INVALID_PATH = "Unknown"
# used to indicate a conan reference is invalid
INVALID_CONAN_REF = "Invalid/0.0.1@NA/NA"
DEBUG_LEVEL = int(os.getenv("CONAN_UNIFIED_API_DEBUG_LEVEL", "0"))
CONAN_LOG_PREFIX = "CONAN: "

conan_pkg_info = distribution("conan")
conan_version = Version(conan_pkg_info.version)


def str2bool(value: str) -> bool:
    """ Own impl. isntead of distutils.util.strtobool
      because distutils will be deprecated """
    value = value.lower()
    if value in {'yes', 'true', 'y', '1'}:
        return True
    if value in {'no', 'false', 'n', '0'}:
        return False
    return False

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
