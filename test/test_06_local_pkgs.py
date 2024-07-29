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


def test_inspect(conan_api):
    inspect = conan_api.inspect(TEST_REF)
    assert inspect.get("name") == ConanRef.loads(TEST_REF).name
    assert inspect.get("generators") == ["txt", "cmake"]

    inspect = conan_api.inspect(TEST_REF, ["no_copy_source"])
    assert inspect["no_copy_source"] == True

def test_conan_find_local_pkg(repo_paths):
    """
    Test, if get_package installs the package and returns the path and check it again.
    The bin dir in the package must exist (indicating it was correctly downloaded)
    """
    conan_remove_ref(TEST_REF)
    conan_install_ref(TEST_REF)
    conan = ConanApi().init_api()
    pkgs = conan.find_best_matching_packages(ConanRef.loads(TEST_REF))
    assert len(pkgs) == 1 # default options are filtered

