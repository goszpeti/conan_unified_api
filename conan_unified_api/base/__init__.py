
from importlib.metadata import distribution
import os
from packaging.version import Version

INVALID_PATH = "Unknown"
# used to indicate a conan reference is invalid
INVALID_CONAN_REF = "Invalid/0.0.1@NA/NA"
DEBUG_LEVEL = int(os.getenv("CONAN_UNIFIED_API_DEBUG_LEVEL", "0"))
CONAN_LOG_PREFIX = "CONAN: "

conan_pkg_info = distribution("conan")
conan_version = Version(conan_pkg_info.version)
