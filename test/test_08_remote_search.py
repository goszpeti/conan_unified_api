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

def test_info_simple(conan_api):
    # ref needs to be in a remote
    info = conan_api.info(TEST_REF_OFFICIAL)
    assert len(info) == 1
    assert info[0].get("binary_remote") == "local"
    assert info[0].get("reference") == TEST_REF_OFFICIAL.split("@")[0]


def test_info_transitive_reqs(conan_api):
    # TODO: let's hope it does not change on the server... 
    info = conan_api.info("pybind11/2.12.0")
    assert len(info) == 1
    assert info[0].get("binary_remote") == "conancenter"
    assert info[0].get("reference") == "pybind11/2.12.0"

    assert info[1].get("reference") == "pybind11/2.12.0" # TODO


def test_inspect(conan_api):
    inspect = conan_api.inspect(TEST_REF)
    assert inspect.get("name") == ConanRef.loads(TEST_REF).name
    assert inspect.get("generators") == ["txt", "cmake"]

    inspect = conan_api.inspect(TEST_REF, ["no_copy_source"])
    assert inspect["no_copy_source"] == True


@pytest.mark.conanv1
def test_conan_get_conan_buildinfo():
    """
    Check, that get_conan_buildinfo actually retrieves as a string for the linux pkg 
    """
    conan = ConanApi().init_api()
    LINUX_X64_GCC9_SETTINGS = {'os': 'Linux', 'arch': 'x86_64', 'compiler': 'gcc', 
        "compiler.libcxx": "libstdc++11",'compiler.version': '9', 'build_type': 'Release'}
    buildinfo = conan.get_conan_buildinfo(ConanRef.loads(TEST_REF), LINUX_X64_GCC9_SETTINGS)
    assert "USER_example" in buildinfo
    assert "ENV_example" in buildinfo


def test_conan_find_remote_pkg(repo_paths):
    """
    Test, if search_package_in_remotes finds a package for the current system and the specified options.
    The function must find exactly one pacakge, which uses the spec. options and corresponds to the
    default settings.
    """
    conan_remove_ref(TEST_REF)
    conan = ConanApi().init_api()
    default_settings = conan.get_default_settings()

    pkgs = conan.find_best_matching_package_in_remotes(ConanRef.loads(TEST_REF), 
                                                        {"shared": "True"})
    assert len(pkgs) > 0
    pkg = pkgs[0]
    assert {"shared": "True"}.items() <= pkg["options"].items()

    for setting in default_settings:
        if setting in pkg["settings"].keys():
            if "compiler." in setting: # don't evaluate comp. details
                continue
            assert default_settings[setting] in pkg["settings"][setting]

def test_conan_not_find_remote_pkg_wrong_opts(repo_paths):
    """
    Test, if a wrong Option return causes an error.
    Empty list must be returned and the error be logged.
    """
    conan_remove_ref(TEST_REF)
    conan = ConanApi().init_api()
    pkg = conan.find_best_matching_package_in_remotes(ConanRef.loads(TEST_REF),  
                                                      {"BogusOption": "True"})
    assert not pkg

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

# @pytest.mark.conanv2 TODO create package for it
def test_compiler_no_settings(repo_paths, capfd):
    """
    Test, if a package with no settings at all can install
    The actual installaton must not return an error.
    """
    ref = "nocompsettings/1.0.0@local/no_sets"
    conan_remove_ref(ref)
    capfd.readouterr() # remove can result in error message - clear
    conan = ConanApi().init_api()

    id, package_folder = conan.get_path_or_auto_install(ConanRef.loads(ref))
    assert (package_folder / "bin").is_dir()
    captured = capfd.readouterr()
    assert "ERROR" not in captured.err
    assert "Can't find a matching package" not in captured.err
    conan_remove_ref(ref)

def test_search_for_all_packages(repo_paths):
    """ Test, that an existing ref will be found in the remotes. """
    conan = ConanApi()
    res = conan.search_recipe_all_versions_in_remotes(ConanRef.loads(TEST_REF))
    ref = ConanRef.loads(TEST_REF)  # need to convert @_/_
    assert str(ref) in str(res)