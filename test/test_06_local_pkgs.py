
import pytest
from test import TEST_REF, TEST_REF_OFFICIAL, TEST_REMOTE_NAME, test_ref_obj, test_ref_official_obj
from test.conan_helper import conan_install_ref, conan_remove_ref, get_profiles

from conan_unified_api.types import ConanPkgRef, ConanRef
from conan_unified_api import conan_version
from conan_unified_api import ConanUnifiedApi
from conan_unified_api.common import ConanUnifiedApi

def test_inspect(conan_api: ConanUnifiedApi):
    inspect = conan_api.inspect(TEST_REF)
    assert inspect.get("name") == ConanRef.loads(TEST_REF).name
    assert inspect.get("generators") == ("CMakeDeps", "CMakeToolchain")

    # objects are not identical -> compare arbitrary values 
    inspect == conan_api.inspect(test_ref_obj)
    assert inspect.get("name") == ConanRef.loads(TEST_REF).name
    assert inspect.get("generators") == ("CMakeDeps", "CMakeToolchain")

    inspect = conan_api.inspect(TEST_REF, ["no_copy_source"], TEST_REMOTE_NAME)
    assert inspect["no_copy_source"] == True


def test_alias(conan_api: ConanUnifiedApi):
    """ Test that alias creates the ref locally -> will only have export folder """
    if conan_version.major == 2: # skip for conan 2
        return
    alias_ref = "example/(1.1.1)@user/new_channel"
    try:
        conan_api.alias(alias_ref, TEST_REF)
        assert conan_api.get_export_folder(ConanRef.loads(alias_ref)).exists()
    finally:
        conan_remove_ref(alias_ref)

def test_conan_find_local_pkg(conan_api: ConanUnifiedApi):
    """
    Test, if get_package installs the package and returns the path and check it again.
    The bin dir in the package must exist (indicating it was correctly downloaded)
    """
    conan_remove_ref(TEST_REF)
    conan_install_ref(TEST_REF)
    pkgs = conan_api.find_best_matching_packages(ConanRef.loads(TEST_REF))
    assert len(pkgs) == 1 # default options are filtered


def test_get_export_folder(conan_api: ConanUnifiedApi):
    conan_install_ref(TEST_REF)
    assert (conan_api.get_export_folder(TEST_REF) / "conanfile.py").exists()
    assert (conan_api.get_export_folder(test_ref_obj) / "conanfile.py").exists()


def test_get_conanfile_path(conan_api: ConanUnifiedApi):
    conanfile_path = conan_api.get_conanfile_path(TEST_REF)
    assert conanfile_path.is_file()
    assert conanfile_path.name == "conanfile.py"
    assert conanfile_path == conan_api.get_conanfile_path(test_ref_obj)


def test_get_all_local_refs(conan_api: ConanUnifiedApi):
    conan_install_ref(TEST_REF)
    conan_install_ref(TEST_REF_OFFICIAL)

    refs = conan_api.get_all_local_refs()
    assert test_ref_obj in refs
    assert test_ref_official_obj in refs


def test_get_local_pkg_from_id(conan_api: ConanUnifiedApi):
    conan_install_ref(TEST_REF)
    pkgs = conan_api.get_local_pkgs_from_ref(TEST_REF)

    pkg = conan_api.get_local_pkg_from_id(ConanPkgRef(TEST_REF, pkgs[0].get("id")))
    
    assert pkg == pkgs[0]

def test_get_local_pkg_from_path(conan_api: ConanUnifiedApi):
    pass


def test_get_options_with_default_values(conan_api: ConanUnifiedApi):
    available_options, default_options = conan_api.get_options_with_default_values(test_ref_obj)
    assert conan_api._are_option_compatible(available_options, {'shared': [
        'True', 'False'], 'fPIC2': ['True', 'False'], 'variant': ['ANY']})
    conan_api._are_option_compatible(
        default_options, {"shared": True, 'fPIC2': True, "variant": "var1"})

def test_get_local_pkgs_from_ref(conan_api: ConanUnifiedApi):
    # install all packages
    for profile in get_profiles():
        for option in ["True", "False"]:
            conan_install_ref(TEST_REF, "-o shared=" + option, profile)
    pkgs = conan_api.get_local_pkgs_from_ref(TEST_REF)
    if conan_version.major == 1:
        assert len(pkgs) == 4
    else:
        assert len(pkgs) >= 2  # TODO this seems to be a bug in conanV2


def test_get_package_folder(conan_api: ConanUnifiedApi):
    pkgs = conan_api.get_local_pkgs_from_ref(TEST_REF)
    pkg_path = conan_api.get_package_folder(TEST_REF, pkgs[0].get("id", ""))
    assert pkg_path.exists() # TODO better check


def test_remove_reference(conan_api: ConanUnifiedApi):
    id, path = conan_api.get_path_with_auto_install(TEST_REF)
    assert path.exists()

    conan_api.remove_reference(TEST_REF)
    assert not path.exists()


@pytest.mark.parametrize("ref, option_key, option_value",
                         [(TEST_REF, "shared", True),
                          (TEST_REF_OFFICIAL, "", None),
                          ],)
def test_find_best_matching_local_package(conan_api: ConanUnifiedApi, ref: str, 
                                          option_key: str, option_value):
    """ Test find a package in the local cache """
    option = None
    if option_key:
        option = {option_key: option_value}
    conan_api.get_path_with_auto_install(test_ref_obj, option)
    matching_pkg = conan_api.find_best_matching_local_package(TEST_REF, option)
    assert matching_pkg.get("id")
    assert matching_pkg.get("options")
    assert matching_pkg.get("settings")

    if option_key:
        assert matching_pkg.get("options", {})[option_key] == option_value
    

def test_get_best_matching_local_package_path(conan_api: ConanUnifiedApi):
    # TODO add conan options as test parameter
    conan_install_ref(TEST_REF)
    
    id, path = conan_api.get_best_matching_local_package_path(test_ref_obj)
    
    pkg = conan_api.get_local_pkg_from_path(test_ref_obj, path)

    assert path.exists()
    assert pkg.get("id") == id
