
import os
from pathlib import Path
import platform
import tempfile
import pytest
from conan_unified_api.base.helper import str2bool
from conan_unified_api.unified_api import ConanUnifiedApi
from conan_unified_api import conan_version


def test_get_settings_file_path(conan_api: ConanUnifiedApi):
    settings_path = conan_api.get_settings_file_path()
    assert settings_path.name == "settings.yml"
    assert settings_path.is_file()


def test_get_config_file_path(conan_api: ConanUnifiedApi):
    config_path = conan_api.get_config_file_path()
    assert config_path.suffix == ".conf"
    assert config_path.is_file()


def test_get_config_entry(conan_api: ConanUnifiedApi):
    if conan_version.major == 1:
        config_entry_name = "general.non_interactive" # set by fixture
    else:
        # no adding config api yet, so hack it 
        config = conan_api.get_config_file_path().read_text()
        # remove commented out lines
        configs = {}
        for line in config.split("\n"):
            if not line.lstrip().startswith("#") and line:
                name = line.split("=")[0].strip()
                value = line.split("=")[1].strip()
                configs[name] = value
        config_entry_name = "core:non_interactive"
        if config_entry_name not in config:
            config += f"\n{config_entry_name}=True\n"
            conan_api.get_config_file_path().write_text(config)
    conan_api.init_api() # reads config only on init
    entry_value = conan_api.get_config_entry(config_entry_name)
    assert entry_value is not None

    if conan_version.major == 1:
        assert str2bool(entry_value)
    else:
        assert entry_value == True


def test_get_revisions_enabled(conan_api: ConanUnifiedApi):
    entry_value = conan_api.get_revisions_enabled()
    assert entry_value is not None
    assert entry_value


def test_get_user_home_path(conan_api: ConanUnifiedApi):
    path = conan_api.get_user_home_path()
    assert path.is_dir()
    assert (path / "settings.yml").exists() # ok for both Conan 1 and 2


def test_get_storage_path(conan_api: ConanUnifiedApi):
    path = conan_api.get_storage_path()
    assert path.is_dir()
    # TODO: Extend test a little bit...

@pytest.mark.conanv1
def test_conan_short_path_root(conan_api: ConanUnifiedApi):
    """ Test, that short path root can be read. """
    if conan_version.major == 2:
        return
    new_short_home = Path(tempfile.gettempdir()) / "._myconan_short"
    os.environ["CONAN_USER_HOME_SHORT"] = str(new_short_home)
    if platform.system() == "Windows":
        assert conan_api.get_short_path_root() == new_short_home
    else:
        assert not conan_api.get_short_path_root().exists()
    os.environ.pop("CONAN_USER_HOME_SHORT")
