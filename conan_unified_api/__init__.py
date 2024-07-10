"""
Convenience access to all user related classes and factory for conan api.
"""
from importlib.metadata import distribution
from pathlib import Path

from .base import conan_version
from .cache.conan_cache import ConanInfoCache
from .unified_api import ConanUnifiedApi

PKG_NAME = "conan_unified_api"
__version__ = distribution(PKG_NAME)

# Paths to find folders - points to the folder of this file
# must be initialized later, otherwise setup.py can't parse this file

base_path = Path(__file__).absolute().parent


def ConanApiFactory() -> ConanUnifiedApi:
    """ Instantiate ConanApi in the correct version """
    if conan_version.major == 1:
        from conan_unified_api.conanV1 import ConanApi
        return ConanApi()
    elif conan_version.major == 2:
        from .conanV2 import ConanApi
        return ConanApi()
    else:
        raise RuntimeError("Can't recognize Conan version")

