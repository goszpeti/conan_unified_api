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
from conan_unified_api.unified_api import ConanUnifiedApi


def test_get_path_or_install(conan_api: ConanUnifiedApi):
    """
    Test, if get_package installs the package and returns the path and check it again.
    The bin dir in the package must exist (indicating it was correctly downloaded)
    """
    dir_to_check = "bin"
    conan_remove_ref(TEST_REF)

    # Gets package path / installs the package
    id, package_folder = conan_api.get_path_or_auto_install(ConanRef.loads(TEST_REF))
    assert (package_folder / dir_to_check).is_dir()
    # check again for already installed package
    id, package_folder = conan_api.get_path_or_auto_install(ConanRef.loads(TEST_REF))
    assert (package_folder / dir_to_check).is_dir()


def test_get_path_or_install_manual_options(conan_api: ConanUnifiedApi):
    """
    Test, if a package with options can install.
    The actual installaton must not return an error and non given options be merged with default options.
    """
    # This package has an option "shared" and is fairly small.
    conan_remove_ref(TEST_REF)
    id, package_folder = conan_api.get_path_or_auto_install(
        ConanRef.loads(TEST_REF), {"shared": "True"})
    if platform.system() == "Windows":
        assert (package_folder / "bin" / "python.exe").is_file()
    elif platform.system() == "Linux":
        assert (package_folder / "bin" / "python").is_file()

# @pytest.mark.conanv2 TODO: Create v2 compatible testcase
def test_install_with_any_settings(mocker, capfd):
    """
    Test, if a package with <setting>=Any flags can install
    The actual installaton must not return an error.
    """
    # mock the remote response
    conan_remove_ref(TEST_REF)
    # Create the "any" package
    conan = ConanApi().init_api()
    assert conan.install_package(ConanRef.loads(TEST_REF), {
        'id': '325c44fdb228c32b3de52146f3e3ff8d94dddb60', 'options': {},
        'settings': {'arch_build': 'any', 'os_build': 'Linux', "build_type": "ANY"},
        'requires': [], 'outdated': False},)
    captured = capfd.readouterr()
    assert "ERROR" not in captured.err
    assert "Cannot install package" not in captured.err

# @pytest.mark.conanv2 TODO create package for it


def test_install_compiler_no_settings(conan_api: ConanUnifiedApi, capfd):
    """
    Test, if a package with no settings at all can install
    The actual installaton must not return an error.
    """
    ref = "nocompsettings/1.0.0@local/no_sets"
    conan_remove_ref(ref)
    capfd.readouterr() # remove can result in error message - clear

    id, package_folder = conan_api.get_path_or_auto_install(ConanRef.loads(ref))
    assert (package_folder / "bin").is_dir()
    captured = capfd.readouterr()
    assert "ERROR" not in captured.err
    assert "Can't find a matching package" not in captured.err
    conan_remove_ref(ref)


@pytest.mark.conanv1
def test_conan_get_conan_buildinfo():
    """
    Check, that get_conan_buildinfo actually retrieves as a string for the linux pkg 
    This exectues an install under the hood, thus the category
    """
    conan = ConanApi().init_api()
    LINUX_X64_GCC9_SETTINGS = {'os': 'Linux', 'arch': 'x86_64', 'compiler': 'gcc',
                               "compiler.libcxx": "libstdc++11", 'compiler.version': '9', 'build_type': 'Release'}
    buildinfo = conan.get_conan_buildinfo(
        ConanRef.loads(TEST_REF), LINUX_X64_GCC9_SETTINGS)
    assert "USER_example" in buildinfo
    assert "ENV_example" in buildinfo
