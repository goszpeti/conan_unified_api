
from test import TEST_REF, TEST_REMOTE_NAME
from test.conan_helper import conan_install_ref, conan_remove_ref

from conan_unified_api.types import ConanRef
from conan_unified_api.unified_api import ConanUnifiedApi


def test_inspect(conan_api: ConanUnifiedApi):
    inspect = conan_api.inspect(TEST_REF)
    assert inspect.get("name") == ConanRef.loads(TEST_REF).name
    assert inspect.get("generators") == ("CMakeDeps", "CMakeToolchain")

    inspect = conan_api.inspect(TEST_REF, ["no_copy_source"], TEST_REMOTE_NAME)
    assert inspect["no_copy_source"] == True


def test_alias(conan_api: ConanUnifiedApi):
    pass
    #def alias(self, conan_ref: Union[ConanRef, str], conan_target_ref: Union[ConanRef, str]):


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


#     @abstractmethod
#     def get_conanfile_path(self, conan_ref: ConanRef) -> Path:
#         """ Get local conanfile path. If it is not localy available, download it."""
#         raise NotImplementedError

#     @abstractmethod
#     def get_package_folder(self, conan_ref: ConanRef, package_id: str) -> ConanPackagePath:
#         " Get the fully resolved pkg path from the ref and the specific package (id) "
#         raise NotImplementedError

# @abstractmethod
# def remove_reference(self, conan_ref: ConanRef, pkg_id: str = ""):
#     """ Remove a conan reference and it's package if specified via id """
#     raise NotImplementedError

# @abstractmethod
# def find_best_matching_local_package(self, conan_ref: ConanRef,
#                                         conan_options: Optional[ConanOptions] = None) -> ConanPkg:
#     """ Find a package in the local cache """
#     raise NotImplementedError

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
# def get_local_pkgs_from_ref(self, conan_ref: ConanRef) -> List[ConanPkg]:
#     """ Returns all installed pkg ids for a reference. """
#     raise NotImplementedError

# @abstractmethod
# def get_local_pkg_from_id(self, pkg_ref: ConanPkgRef) -> ConanPkg:
#     """ Returns an installed pkg from reference and id """
#     raise NotImplementedError

# @abstractmethod
# def get_local_pkg_from_path(self, conan_ref: ConanRef, path: Path):
#     """ For reverse lookup - give info from path """
#     raise NotImplementedError
