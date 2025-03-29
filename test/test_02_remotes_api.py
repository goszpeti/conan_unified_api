
import pytest
from pytest_check import check
from conan_unified_api.unified_api import ConanBaseUnifiedApi
from test.conan_helper import disable_remote, remove_remote, add_remote, TEST_REMOTE_NAME
from test import TEST_REMOTE_URL, TEST_REMOTE_USER, time_function

@pytest.fixture
def new_remote():
    """ Fixture factory for multiple new remotes. Cleans up after each testcase. """
    remotes = []

    def _add_remote(name="new1", url="http://localhost:9303"):
        remove_remote(name)
        add_remote(name, url)
        remotes.append(name)
        return name, url

    yield _add_remote

    for remote in remotes:
        remove_remote(remote)


def test_add_remove_remotes(conan_api: ConanBaseUnifiedApi):
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


def test_disable_remotes(conan_api: ConanBaseUnifiedApi, new_remote):
    new_remote_name, _ = new_remote()
    remote = conan_api.get_remote(new_remote_name)
    assert remote
    assert not remote.disabled

    conan_api.disable_remote(new_remote_name, True)
    remote = conan_api.get_remote(new_remote_name)
    assert remote
    assert remote.disabled

    conan_api.disable_remote(new_remote_name, False)
    remote = conan_api.get_remote(new_remote_name)
    assert remote
    assert not remote.disabled

def test_get_remote_user_info(conan_api: ConanBaseUnifiedApi):
    """ Check that get_remote_user_info returns a tuple of name and login
      state for the test remote """
    info = conan_api.get_remote_user_info(TEST_REMOTE_NAME)
    assert info == (TEST_REMOTE_USER, True)


def test_get_remotes(conan_api: ConanBaseUnifiedApi, new_remote):
    """ Test that get_remotes returns remote objects and cotains the test remote and 
    the new remote. Also check include_disabled flag.
    """
    new_remote_name, _ = new_remote()

    remotes = conan_api.get_remotes()
    assert len(remotes) >= 2
    found_remote = 0
    for remote in remotes:
        if remote.name ==  TEST_REMOTE_NAME:
            found_remote += 1
        if remote.name == new_remote_name:
            found_remote += 1
    assert found_remote == 2
    disable_remote(new_remote_name)
    remotes = conan_api.get_remotes(include_disabled=True)
    assert remotes[-1].name == new_remote_name


def test_get_remotes_names(conan_api: ConanBaseUnifiedApi, new_remote):
    new_remote_name, _ = new_remote()

    disable_remote(new_remote_name)

    remote_names = conan_api.get_remote_names()
    assert TEST_REMOTE_NAME in remote_names
    assert new_remote_name not in remote_names

    remote_names = conan_api.get_remote_names(include_disabled=True)
    assert TEST_REMOTE_NAME in remote_names
    assert new_remote_name in remote_names


def test_get_remote(conan_api: ConanBaseUnifiedApi):
    remote = conan_api.get_remote(TEST_REMOTE_NAME)
    assert remote  # not None
    assert remote.name == TEST_REMOTE_NAME
    assert remote.url == TEST_REMOTE_URL


def test_update_remotes(conan_api: ConanBaseUnifiedApi, new_remote):
    new_remote_name, _ = new_remote()

    conan_api.update_remote(new_remote_name, "http://localhost:9304", True)

    remote = conan_api.get_remote(new_remote_name)
    assert remote  # not None
    assert remote.url == "http://localhost:9304"
    assert remote.verify_ssl

    # test reorder
    conan_api.update_remote(new_remote_name, "http://localhost:9304", True, 0)
    remotes = conan_api.get_remotes()
    assert remotes[0].name == new_remote_name


def test_rename_remotes(conan_api: ConanBaseUnifiedApi, new_remote):
    new_remote_name, _ = new_remote()

    renamed_name = "new_ng_last_final"
    conan_api.rename_remote(new_remote_name, renamed_name)
    with check:
        assert "new_ng_last_final" in conan_api.get_remote_names()
    with check:
        assert new_remote_name not in conan_api.get_remote_names()

    remove_remote(renamed_name)


def test_login_remote(conan_api: ConanBaseUnifiedApi):
    conan_api.login_remote(TEST_REMOTE_NAME, "demo", "demo")

    with pytest.raises(Exception) as excinfo:
        conan_api.login_remote(TEST_REMOTE_NAME, "demo", "abc")
    
