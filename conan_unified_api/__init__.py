"""
This module contains all interfaces and backend functions
containing the applications core functionality.
Settings need to be already set up for usage.
"""
from importlib.metadata import distribution, PackageNotFoundError
import os
from pathlib import Path
from packaging.version import Version

from .unified_api import ConanCommonUnifiedApi
from .conan_cache import ConanInfoCache

PKG_NAME = "conan_unified_api"
INVALID_PATH = "Unknown"
# used to indicate a conan reference is invalid
INVALID_CONAN_REF = "Invalid/0.0.1@NA/NA"
DEBUG_LEVEL = int(os.getenv("CONAN_UNIFIED_API_DEBUG_LEVEL", "0"))


conan_pkg_info = distribution("conan")

conan_version = Version(conan_pkg_info.version)

# Paths to find folders - points to the folder of this file
# must be initialized later, otherwise setup.py can't parse this file

base_path = Path(__file__).absolute().parent

try:
    pkg_info = distribution(PKG_NAME)
    __version__ = pkg_info.version
    REPO_URL = pkg_info.metadata.get("home-page", "")  # type: ignore
    AUTHOR = pkg_info.metadata.get("author", "")  # type: ignore
except PackageNotFoundError:  # pragma: no cover
    # For local usecases, when there is no distribution
    __version__ = "1.0.0"
    REPO_URL = ""
    AUTHOR = ""


def ConanApiFactory() -> ConanCommonUnifiedApi:
    """ Isntantiate ConanApi in the correct version """
    if conan_version.major == 1:
        from conan_unified_api.conan_wrapper.conanV1 import ConanApi
        return ConanApi()
    elif conan_version.major == 2:
        from .conanV2 import ConanApi
        return ConanApi()
    else:
        raise RuntimeError("Can't recognize Conan version")

