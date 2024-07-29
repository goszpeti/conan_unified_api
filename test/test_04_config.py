
import os
from pathlib import Path
import platform
import tempfile
import pytest
from conan_unified_api.unified_api import ConanUnifiedApi
from test.conan_helper import disable_remote, remove_remote, add_remote, TEST_REMOTE_NAME
from test import TEST_REMOTE_URL, TEST_REMOTE_USER, time_function



def test_get_remote(conan_api: ConanUnifiedApi):
    remote = conan_api.get_remote(TEST_REMOTE_NAME)
    assert remote  # not None
    assert remote.name == TEST_REMOTE_NAME
    assert remote.url == TEST_REMOTE_URL

# @abstractmethod
# def get_settings_file_path(self) -> Path:
#     """ Return conan settings file path (settings.yml) """
#     raise NotImplementedError

# @abstractmethod
# def get_config_file_path(self) -> Path:
#     """ Return conan config file path (conan.conf) """
#     raise NotImplementedError

# @abstractmethod
# def get_config_entry(self, config_name: str, default_value: Any) -> Any:
#     """ Return a conan config entry value (conan.conf). 
#     Use default_value for non existing values. 
#     Can not raise an exception.
#     """
#     raise NotImplementedError

# @abstractmethod
# def get_revisions_enabled(self) -> bool:
#     """ Return if revisions are enabled for Conan V1. Always true in V2 mode. """
#     raise NotImplementedError

# @abstractmethod
# def get_user_home_path(self) -> Path:
#     """ Return Conan user home path, where e.g. settings reside """
#     raise NotImplementedError

# @abstractmethod
# def get_storage_path(self) -> Path:
#     """ Return Conan storage path, where packages are saved """
#     raise NotImplementedError



@pytest.mark.conanv1
def test_conan_short_path_root(conan_api: ConanUnifiedApi):
    """ Test, that short path root can be read. """
    new_short_home = Path(tempfile.gettempdir()) / "._myconan_short"
    os.environ["CONAN_USER_HOME_SHORT"] = str(new_short_home)
    if platform.system() == "Windows":
        assert conan_api.get_short_path_root() == new_short_home
    else:
        assert not conan_api.get_short_path_root().exists()
    os.environ.pop("CONAN_USER_HOME_SHORT")
