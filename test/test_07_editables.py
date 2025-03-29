import os

import pytest
from conan_unified_api.types import ConanRef
from test import TEST_REF
from pytest_check import check

from conan_unified_api import conan_version
from conan_unified_api.unified_api import ConanBaseUnifiedApi
from test.conan_helper import add_editable, remove_editable

TEST_EDITABLE_REF = "example/9.9.9@local/editable"


@pytest.fixture
def editable_path(repo_paths):
    """ An editable target path needs a conanfile.py in it, return the original conanfile path in testdata"""
    path = repo_paths.testdata_path / "conan"
    if conan_version.major == 1:
        path /= "conanfile.py"
    elif conan_version.major == 2:
        path /= "conanfileV2.py"
    return path


@pytest.fixture
def new_editable():
    """ Fixture factory for multiple new editables. Cleans up after each testcase. """
    editable_refs = []

    def _add_editable(ref, path, output_path=None):
        remove_editable(ref) # if it exists with another path
        add_editable(ref, path, output_path)
        editable_refs.append(ref)
        return

    yield _add_editable

    for ref in editable_refs:
        remove_editable(ref)


def test_get_editable(conan_api: ConanBaseUnifiedApi, editable_path, new_editable):
    broken_editable = conan_api.get_editable(TEST_REF)
    with check:
     assert broken_editable is None
    
    new_editable(TEST_EDITABLE_REF, editable_path)
    editable = conan_api.get_editable(TEST_EDITABLE_REF)
    assert editable
    assert editable.conan_ref == TEST_EDITABLE_REF
    assert editable.path == str(editable_path)


def test_get_editables_package_path(conan_api: ConanBaseUnifiedApi, editable_path, new_editable):
    new_editable(TEST_EDITABLE_REF, editable_path)

    assert conan_api.get_editables_package_path(TEST_EDITABLE_REF) == editable_path


def test_get_editables_output_folder(conan_api: ConanBaseUnifiedApi, editable_path, 
                                     new_editable, repo_paths):
    new_editable(TEST_EDITABLE_REF, editable_path, repo_paths.testdata_path)

    assert conan_api.get_editables_output_folder(
        TEST_EDITABLE_REF) == repo_paths.testdata_path


def test_get_editable_references(conan_api: ConanBaseUnifiedApi, new_editable, editable_path):
    new_editable(TEST_EDITABLE_REF, editable_path)
    new_editable(TEST_EDITABLE_REF + "_2", editable_path)

    refs = conan_api.get_editable_references()
    assert ConanRef.loads(TEST_EDITABLE_REF) in refs
    assert ConanRef.loads(TEST_EDITABLE_REF + "_2") in refs


def test_add_remove_editable(conan_api: ConanBaseUnifiedApi, editable_path, repo_paths):
    os.system(f"conan editable remove {TEST_EDITABLE_REF}")

    conan_api.add_editable(TEST_EDITABLE_REF, editable_path, repo_paths.testdata_path)
    editable = conan_api.get_editable(TEST_EDITABLE_REF)
    assert editable
    assert editable.conan_ref == TEST_EDITABLE_REF
    assert editable.path == str(editable_path)
    assert editable.output_folder == str(repo_paths.testdata_path)

    conan_api.remove_editable(TEST_EDITABLE_REF)
    assert conan_api.get_editable(TEST_EDITABLE_REF) is None
