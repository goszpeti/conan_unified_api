
import platform
from conan_unified_api.unified_api import ConanBaseUnifiedApi


def test_get_profiles(conan_api: ConanBaseUnifiedApi):
    profiles = conan_api.get_profiles()
    assert len(profiles) >= 1
    assert "default" in profiles


def test_get_profiles_path(conan_api: ConanBaseUnifiedApi):
    profiles_path = conan_api.get_profiles_path()
    assert (profiles_path / "default").is_file()


def test_get_profile_settings(conan_api: ConanBaseUnifiedApi):
    settings = conan_api.get_profile_settings("default")
    assert settings.get("os") == platform.system()
    assert settings.get("arch") == "x86_64"


def test_get_default_settings(conan_api: ConanBaseUnifiedApi):
    settings = conan_api.get_default_settings()
    assert settings.get("os") == platform.system()
    assert settings.get("arch") == "x86_64"


def test_conan_profile_name_alias_builder(conan_api: ConanBaseUnifiedApi):
    """ Test, that the build_conan_profile_name_alias returns human readable strings. """
    # check empty - should return a default name
    profile_name = conan_api.build_conan_profile_name_alias({})
    assert profile_name == "No Settings"

    # check a partial
    settings = {'os': 'Windows', 'arch': 'x86_64'}
    profile_name = conan_api.build_conan_profile_name_alias(settings)
    assert profile_name == "Windows_x64"

    # check windows
    WINDOWS_x64_VS16_SETTINGS = {'os': 'Windows', 'os_build': 'Windows', 'arch': 'x86_64',
                                 'arch_build': 'x86_64', 'compiler': 'Visual Studio',
                                 'compiler.version': '16', 'compiler.toolset': 'v142',
                                 'build_type': 'Release'}
    profile_name = conan_api.build_conan_profile_name_alias(WINDOWS_x64_VS16_SETTINGS)
    assert profile_name == "Windows_x64_vs16_v142_release"

    # check linux
    LINUX_X64_GCC7_SETTINGS = {'os': 'Linux', 'arch': 'x86_64', 'compiler': 'gcc',
                               'compiler.version': '7.4', 'build_type': 'Debug'}
    profile_name = conan_api.build_conan_profile_name_alias(LINUX_X64_GCC7_SETTINGS)
    assert profile_name == "Linux_x64_gcc7.4_debug"
