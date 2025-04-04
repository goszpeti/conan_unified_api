"""
Convenience access to all user related classes and factory for conan api.
"""

import logging
from importlib.metadata import distribution
from pathlib import Path
from typing import Optional

from .base import conan_version, invalid_path
from .cache.conan_cache import ConanInfoCache
from .common import ConanUnifiedApi

PKG_NAME = "conan_unified_api"
__version__ = distribution(PKG_NAME).version

# Paths to find folders - points to the folder of this file
# must be initialized later, otherwise setup.py can't parse this file

base_path = Path(__file__).absolute().parent


def ConanApiFactory(
    init: bool = True,
    logger: Optional[logging.Logger] = None,
    mute_logging: bool = False,
) -> ConanUnifiedApi:  # noqa: N802
    """Instantiate ConanApi in the correct version"""
    if conan_version.major == 1:
        from conan_unified_api.conan_v1 import ConanApi
    elif conan_version.major == 2:
        from .conan_v2 import ConanApi
    else:
        raise RuntimeError("Can't recognize Conan version")

    return ConanApi(init, logger, mute_logging)


__all__ = [
    "ConanInfoCache",
    "base_path",
    "invalid_path",
]
