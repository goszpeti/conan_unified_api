import os
import tempfile
from pathlib import Path


from conan_unified_api.base.helper import (create_key_value_pair_list, delete_path)
from conan_unified_api.unified_api import ConanBaseUnifiedApi
from conan_unified_api.common import ConanUnifiedApi
from test import TEST_REF_OFFICIAL


def test_delete():
    """ 
    1. Delete file
    2. Delete non-empty directory
    """
    # 1. Delete file
    test_file = Path(tempfile.mkdtemp()) / "test.inf"
    test_file_content = "test"
    with open(str(test_file), "w") as f:
        f.write(test_file_content)
    delete_path(test_file)
    assert not test_file.exists()

    # 2. Delete non-empty directory
    test_dir = Path(tempfile.mkdtemp()) / "test_dir"
    os.makedirs(test_dir)
    test_dir_file = test_dir / "test.inf"
    with open(str(test_dir_file), "w") as f:
        f.write("test")
    delete_path(test_dir)
    assert not test_dir.exists()


def test_create_key_value_list():
    """
    Test, that key value pairs can be extracted as strings. No arrays or other tpyes supported.
    The return value must be a list of strings in the format ["key1=value1", "key2=value2]
    "Any" values are ignored. (case insensitive)
    """
    inp = {"Key1": "Value1"}
    res = create_key_value_pair_list(inp)
    assert res == ["Key1=Value1"]
    inp = {"Key1": "Value1", "Key2": "Value2"}
    res = create_key_value_pair_list(inp)
    assert res == ["Key1=Value1", "Key2=Value2"]
    inp = {"Key1": "Value1", "Key2": "Any"}
    res = create_key_value_pair_list(inp)
    assert res == ["Key1=Value1"]

def test_generate_canonical_ref(conan_api: ConanBaseUnifiedApi):
    ref = conan_api.generate_canonical_ref(TEST_REF_OFFICIAL.split("@")[0])
    assert ref == TEST_REF_OFFICIAL


def test_resolve_default_options(conan_api: ConanUnifiedApi):
    """
    Test, if different kind of types of default options can be converted to a dict
    Dict is expected.
    """
    str_val = "option=value"
    ret = conan_api._resolve_default_options(str_val)
    assert ret.items()

    tup_val = ("option=value", "options2=value2")
    ret = conan_api._resolve_default_options(tup_val)
    assert ret.items()

    list_val = ["option=value", "options2=value2"]
    ret = conan_api._resolve_default_options(list_val)
    assert ret.items()
