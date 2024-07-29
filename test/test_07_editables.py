import os
import platform
import tempfile
from pathlib import Path

import pytest
from test import TEST_REF, TEST_REF_OFFICIAL
from test.conan_helper import conan_install_ref, conan_remove_ref

from conan_unified_api import ConanApiFactory as ConanApi
from conan_unified_api.base.helper import create_key_value_pair_list
from conan_unified_api.types import ConanRef
