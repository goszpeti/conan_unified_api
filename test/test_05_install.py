import platform

from test import TEST_REF, TEST_REF_NO_SETTINGS, TEST_REMOTE_NAME
from test.conan_helper import conan_remove_ref

from conan_unified_api import conan_version
from conan_unified_api.types import ConanRef
from conan_unified_api.unified_api import ConanBaseUnifiedApi


def test_get_path_or_install(conan_api: ConanBaseUnifiedApi):
    """
    Test, if get_package installs the package and returns the path and check it again.
    The bin dir in the package must exist (indicating it was correctly downloaded)
    """
    dir_to_check = "bin"
    conan_remove_ref(TEST_REF)

    # Gets package path / installs the package
    id, package_folder = conan_api.get_path_with_auto_install(ConanRef.loads(TEST_REF))
    assert (package_folder / dir_to_check).is_dir()
    # check again for already installed package
    id, package_folder = conan_api.get_path_with_auto_install(ConanRef.loads(TEST_REF))
    assert (package_folder / dir_to_check).is_dir()


def test_get_path_or_install_manual_options(conan_api: ConanBaseUnifiedApi):
    """
    Test, if a package with options can install.
    The actual installaton must not return an error and non given options be merged with default options.
    """
    # This package has an option "shared" and is fairly small.
    conan_remove_ref(TEST_REF)
    id, package_folder = conan_api.get_path_with_auto_install(
        ConanRef.loads(TEST_REF), {"shared": "True"})
    if platform.system() == "Windows":
        assert (package_folder / "bin" / "python.exe").is_file()
    elif platform.system() == "Linux":
        assert (package_folder / "bin" / "python").is_file()


def test_install_with_any_settings(mocker, capfd, conan_api: ConanBaseUnifiedApi):
    """
    Test, if a package with <setting>=Any flags can install
    The actual installaton must not return an error.
    """
    if conan_version.major == 2:  # TODO create package for it
        return
    # mock the remote response
    conan_remove_ref(TEST_REF)
    # Create the "any" package
    assert conan_api.install_package(ConanRef.loads(TEST_REF), {
        'id': '325c44fdb228c32b3de52146f3e3ff8d94dddb60', 'options': {},
        'settings': {'arch_build': 'any', 'os_build': 'Linux', "build_type": "ANY"},
        'requires': [], 'outdated': False}, False, TEST_REMOTE_NAME)
    captured = capfd.readouterr()
    assert "ERROR" not in captured.err
    assert "Cannot install package" not in captured.err

def test_install_compiler_no_settings(conan_api: ConanBaseUnifiedApi, capfd):
    """
    Test, if a package with no settings at all can install
    The actual installaton must not return an error.
    """
    if conan_version.major == 2:  # FIXME: test does not work yet!
        return
    ref = TEST_REF_NO_SETTINGS
    conan_remove_ref(ref)
    capfd.readouterr() # remove can result in error message - clear

    id, package_folder = conan_api.get_path_with_auto_install(ConanRef.loads(ref))
    assert (package_folder / "bin").is_dir()
    captured = capfd.readouterr()
    assert "ERROR" not in captured.err
    assert "Can't find a matching package" not in captured.err
    conan_remove_ref(ref)



def test_conan_get_conan_buildinfo(conan_api: ConanBaseUnifiedApi):
    """
    Check, that get_conan_buildinfo actually retrieves as a string for the linux pkg 
    This exectues an install under the hood, thus the category
    """
    if conan_version.major == 2: # not implemented yet
        return
    LINUX_X64_GCC9_SETTINGS = {'os': 'Linux', 'arch': 'x86_64', 'compiler': 'gcc',
                               "compiler.libcxx": "libstdc++11", 'compiler.version': '9', 'build_type': 'Release'}
    buildinfo = conan_api.get_conan_buildinfo(
        ConanRef.loads(TEST_REF), LINUX_X64_GCC9_SETTINGS)
    assert "USER_example" in buildinfo
    assert "ENV_example" in buildinfo
