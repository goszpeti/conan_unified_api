
import pytest
from test import TEST_REF, TEST_REF_OFFICIAL, TEST_REMOTE_NAME, test_ref_obj
from test.conan_helper import conan_install_ref, conan_remove_ref, get_profiles

from conan_unified_api.types import ConanRef
from conan_unified_api.unified_api import ConanUnifiedApi

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


@pytest.mark.skip(reason="implementaion not finished yet")
def test_alias(conan_api: ConanUnifiedApi):
    alias_ref = "example/1.1.1@user/new_channel"
    conan_api.alias(alias_ref, TEST_REF)
    assert conan_api.get_local_pkgs_from_ref(ConanRef.loads(alias_ref))

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


def test_get_local_pkgs_from_ref(conan_api: ConanUnifiedApi):
    # install all packages
    for profile in get_profiles():
        for option in ["True", "False"]:
            conan_install_ref(TEST_REF, "-o shared=" + option, profile)
    pkgs = conan_api.get_local_pkgs_from_ref(TEST_REF)
    assert len(pkgs) == 4


def test_get_package_folder(conan_api: ConanUnifiedApi):
    pkgs = conan_api.get_local_pkgs_from_ref(TEST_REF)
    pkg_path = conan_api.get_package_folder(TEST_REF, pkgs[0].get("id", ""))
    assert pkg_path.exists() # TODO better check

# @abstractmethod
# def remove_reference(self, conan_ref: ConanRef, pkg_id: str = ""):
#     """ Remove a conan reference and it's package if specified via id """
#     raise NotImplementedError


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
    conan_api.get_path_or_auto_install(test_ref_obj, option)
    matching_pkg = conan_api.find_best_matching_local_package(TEST_REF, option)
    assert matching_pkg.get("id")
    assert matching_pkg.get("options")
    assert matching_pkg.get("settings")

    if option_key:
        assert matching_pkg.get("options", {})[option_key] == option_value
    

# @abstractmethod
# def get_best_matching_local_package_path(self, conan_ref: ConanRef,
#                                             conan_options: Optional[ConanOptions] = None
#                                             ) -> Tuple[ConanPackageId, ConanPackagePath]:
#     " Return the pkg_id and pkg folder of a conan reference, if it is installed. "
#     raise NotImplementedError

# @abstractmethod
# def get_all_local_refs(self) -> List[ConanRef]:
#     """ Returns all locally installed conan references """
#     raise NotImplementedError


# @abstractmethod
# def get_local_pkg_from_id(self, pkg_ref: ConanPkgRef) -> ConanPkg:
#     """ Returns an installed pkg from reference and id """
#     raise NotImplementedError

# @abstractmethod
# def get_local_pkg_from_path(self, conan_ref: ConanRef, path: Path):
#     """ For reverse lookup - give info from path """
#     raise NotImplementedError
