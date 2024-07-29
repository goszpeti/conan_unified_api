""" 
Test order is important for performance and error tracing.
The basic tests have no dependencies to available test data to the server.
Also when tested the conan_cli class functions will be swapped out for faster
internal functions. This is important because they are spawning a new interpreter
every time with an overhead in the region of seconds and are used in setup/teardown functions
multiple times.

"""

from contextlib import contextmanager
from datetime import datetime
import os
from pathlib import Path
from conan_unified_api import ConanApiFactory
from conan_unified_api.base.helper import str2bool


###### Global singleton test object ######
"""
The conan_api holds almost no state (except the cache files)
It could also be an auto session fixture,
but then the helper fcns from conan_helper can't use it
"""
conan_api = ConanApiFactory()
conan_api.init_api()
##########################################


TEST_REF = "example/9.9.9@local/testing"
TEST_REF_OFFICIAL = "example/1.0.0@_/_"
SKIP_CREATE_CONAN_TEST_DATA = str2bool(
    os.getenv("SKIP_CREATE_CONAN_TEST_DATA", "False"))
TEST_REMOTE_NAME = "local"
TEST_REMOTE_URL = "http://127.0.0.1:9300/"
TEST_REMOTE_USER = "demo"


@contextmanager
def time_function(name: str):
    begin_time = datetime.now()
    yield
    end_time = datetime.now()
    action_time = end_time - begin_time
    print(f"Action {name} took {action_time}")


def is_ci_job():
    """ Test runs in CI environment """
    if os.getenv("GITHUB_WORKSPACE"):
        return True
    return False


class PathSetup():
    """ Get the important paths form the source repo. """

    def __init__(self):
        self.test_path = Path(os.path.dirname(__file__))
        self.core_path = self.test_path.parent
        self.testdata_path = self.test_path / "testdata"
