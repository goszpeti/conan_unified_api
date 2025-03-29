
from typing import List
import pytest
from test import (TEST_REF, TEST_REF_NO_SETTINGS, TEST_REF_OFFICIAL, TEST_REMOTE_NAME, 
                  test_ref_obj, test_ref_official_obj)
from test.conan_helper import conan_remove_ref

from conan_unified_api import conan_version
from conan_unified_api.types import ConanPkgRef, ConanRef
from conan_unified_api.unified_api import ConanBaseUnifiedApi


def test_info_simple(conan_api: ConanBaseUnifiedApi):
    # ref needs to be in a remote
    ref = ConanRef.loads(TEST_REF_OFFICIAL.split("@")[0])
    assert conan_api.get_conanfile_path(ref).exists()
    info = conan_api.info(ref)
    assert len(info) == 1
    if conan_version.major == 1:
        assert info[0].get("reference") == TEST_REF_OFFICIAL.split("@")[0]
        # assert info[0].get("binary_remote") == "local"
    elif conan_version.major == 2:  # binary_remote is usually None and reference does not work
        assert info[0].get("name") == ref.name


def test_info_transitive_reqs(conan_api: ConanBaseUnifiedApi):
    info = conan_api.info(TEST_REF_NO_SETTINGS)
    assert len(info) == 2

    if conan_version.major == 1:
        assert info[0].get("binary_remote") == TEST_REMOTE_NAME
        assert info[0].get("reference") == TEST_REF_NO_SETTINGS

        assert info[1].get("reference") == TEST_REF
    elif conan_version.major == 2:  # binary_remote is usually None and reference does not work
       assert info[0].get("name") == ConanRef.loads(TEST_REF_NO_SETTINGS).name
       assert info[1].get("name") == ConanRef.loads(TEST_REF).name

def test_conan_find_remote_pkg(conan_api: ConanBaseUnifiedApi):
    """
    Test, if search_package_in_remotes finds a package for the current system and the specified options.
    The function must find exactly one pacakge, which uses the spec. options and corresponds to the
    default settings.
    """
    conan_remove_ref(TEST_REF)
    default_settings = conan_api.get_default_settings()

    # check that inputing True as bool changes it in return to string 
    # - otherwise we cannot handle later comparisons.
    pkgs, remote = conan_api.find_best_matching_package_in_remotes(ConanRef.loads(TEST_REF),
                                                                   {"shared": True})
    assert remote == TEST_REMOTE_NAME
    assert len(pkgs) > 0
    pkg = pkgs[0]
    assert {"shared": True}.items() <= pkg.get("options", {}).items()

    for setting in default_settings:
        if setting in pkg.get("settings", {}).keys():
            if "compiler." in setting:  # don't evaluate comp. details
                continue
            assert default_settings[setting] in pkg.get("settings", {})[setting]


def test_conan_not_find_remote_pkg_wrong_opts(conan_api: ConanBaseUnifiedApi):
    """
    Test, if a wrong Option return causes an error.
    Empty list must be returned and the error be logged.
    """
    conan_remove_ref(TEST_REF)
    pkg, remote = conan_api.find_best_matching_package_in_remotes(ConanRef.loads(TEST_REF),
                                                                  {"BogusOption": "True"})
    assert not pkg


def test_search_for_all_packages(conan_api: ConanBaseUnifiedApi):
    """ Test, that an existing ref will be found in the remotes. """
    res = conan_api.search_recipe_all_versions_in_remotes(TEST_REF)
    assert len(res) >= 2
    assert TEST_REF in str(res)


@pytest.mark.parametrize("query, remote, expected",
                         [(TEST_REF, "local", [test_ref_obj]),
                          (TEST_REF, "all", [test_ref_obj]),
                          (TEST_REF_OFFICIAL, "local", []),  # does not work
                          ("example*", "local", [test_ref_official_obj, test_ref_obj]),
                         ],)
def test_search_recipes_in_remotes(conan_api: ConanBaseUnifiedApi, query: str, remote: str,
                                   expected: List["ConanRef"]):
    """ Test queries for conan search"""
    assert expected == conan_api.search_recipes_in_remotes(query, remote)


@pytest.mark.parametrize("ref", [TEST_REF, TEST_REF_OFFICIAL],)
def test_get_remote_pkg_from_id(conan_api: ConanBaseUnifiedApi, ref: str):
    """ Test finding the ConanPkg from the ConanPkgRef """
    pkg, _ = conan_api.find_best_matching_package_in_remotes(ref)
    assert len(pkg) >= 1
    assert pkg[0] == conan_api.get_remote_pkg_from_id(
        ConanPkgRef.loads(ref + ":" + pkg[0].get("id", "")))
