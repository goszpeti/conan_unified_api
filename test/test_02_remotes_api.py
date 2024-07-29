
import pytest
from conan_unified_api.unified_api import ConanUnifiedApi
from test.conan_helper import disable_remote, remove_remote, add_remote, TEST_REMOTE_NAME
from test import TEST_REMOTE_URL, TEST_REMOTE_USER, time_function

@pytest.fixture()
def new_remote(name: str = "new1", url: str = "http://localhost:9303"):
    remove_remote(name)
    add_remote(name, url)
    yield name
    remove_remote(name)


def test_add_remove_remotes(conan_api: ConanUnifiedApi):
    """ Check that adding a new remote adds it with all used options.
    Afterwards delete it and check.
    """
    test_remote_name = "new1"
    # remove with cli to ensure that new1 does not exist
    with time_function("remove_remote_setup"):
        remove_remote(test_remote_name)

    orig_remotes = conan_api.get_remotes()
    with time_function("add_remote"):
        conan_api.add_remote(test_remote_name, "http://localhost:9301", False)

    new_remote = conan_api.get_remotes()[-1]
    assert new_remote.name == test_remote_name
    assert new_remote.url == "http://localhost:9301"
    assert not new_remote.verify_ssl

    with time_function("remove_remote"):
        conan_api.remove_remote(test_remote_name)

    assert len(conan_api.get_remotes()) == len(orig_remotes)


def test_disable_remotes(conan_api: ConanUnifiedApi, new_remote: str):
    remote = conan_api.get_remote(new_remote)
    assert remote
    assert not remote.disabled

    conan_api.disable_remote(new_remote, True)
    remote = conan_api.get_remote(new_remote)
    assert remote
    assert remote.disabled

    conan_api.disable_remote(new_remote, False)
    remote = conan_api.get_remote(new_remote)
    assert remote
    assert not remote.disabled

def test_get_remote_user_info(conan_api: ConanUnifiedApi):
    """ Check that get_remote_user_info returns a tuple of name and login
      state for the test remote """
    info = conan_api.get_remote_user_info(TEST_REMOTE_NAME)
    assert info == (TEST_REMOTE_USER, False)


def test_get_remotes(conan_api: ConanUnifiedApi, new_remote: str):
    """ Test that get_remotes returns remote objects and cotains the test remote and 
    conancenter. Also check include_disabled flag.
    """
    remotes = conan_api.get_remotes()
    assert len(remotes) >= 2
    found_remote = False
    for remote in remotes:
        if TEST_REMOTE_NAME == remote.name:
            found_remote = True
    assert found_remote
    disable_remote(new_remote)
    remotes = conan_api.get_remotes(include_disabled=True)
    assert remotes[-1].name == new_remote


def test_get_remotes_names(conan_api: ConanUnifiedApi, new_remote: str):
    disable_remote(new_remote)

    remote_names = conan_api.get_remote_names()
    assert TEST_REMOTE_NAME in remote_names
    assert new_remote not in remote_names

    remote_names = conan_api.get_remote_names(include_disabled=True)
    assert TEST_REMOTE_NAME in remote_names
    assert new_remote in remote_names


def test_get_remote(conan_api: ConanUnifiedApi):
    remote = conan_api.get_remote(TEST_REMOTE_NAME)
    assert remote  # not None
    assert remote.name == TEST_REMOTE_NAME
    assert remote.url == TEST_REMOTE_URL



def test_update_remotes(conan_api: ConanUnifiedApi, new_remote: str):
    conan_api.update_remote(new_remote, "http://localhost:9304", True)

    remote = conan_api.get_remote(new_remote)
    assert remote  # not None
    assert remote.url == "http://localhost:9304"
    assert remote.verify_ssl

    # test reorder
    conan_api.update_remote(new_remote, "http://localhost:9304", True, 0)
    remotes = conan_api.get_remotes()
    assert remotes[0].name == new_remote


def test_rename_remotes():
    pass
