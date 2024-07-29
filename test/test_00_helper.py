import os
import tempfile
from pathlib import Path


from conan_unified_api.base.helper import (delete_path)


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
