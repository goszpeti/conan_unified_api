
from importlib.metadata import distribution
import os
from pathlib import Path
from packaging.version import Version

INVALID_PATH_VALUE = "/INVALIDPATH_6a998a6f-c544-4a32-8414-4dd317d905a3"
invalid_path = Path(INVALID_PATH_VALUE)
DEBUG_LEVEL = int(os.getenv("CONAN_UNIFIED_API_DEBUG_LEVEL", "0"))
CONAN_LOG_PREFIX = "CONAN - "

conan_pkg_info = distribution("conan")
conan_version = Version(conan_pkg_info.version)
