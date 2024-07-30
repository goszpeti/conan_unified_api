import configparser
import ctypes
from datetime import datetime, timedelta
import os
import platform
import shutil
import sys
import time
from pathlib import Path
from subprocess import CalledProcessError, check_output
from threading import Thread
from typing import Generator

import psutil
import pytest
from conan_unified_api import base_path, ConanInfoCache, ConanApiFactory
from conan_unified_api import conan_version
from test import SKIP_CREATE_CONAN_TEST_DATA, TEST_REF, TEST_REF_OFFICIAL, TEST_REMOTE_NAME, TEST_REMOTE_URL, PathSetup, is_ci_job
from test.conan_helper import add_remote, clean_remotes_on_ci, conan_create_and_upload, create_test_ref, get_profiles, login_test_remote
import test.conan_helper

exe_ext = ".exe" if platform.system() == "Windows" else ""
conan_server_thread = None

def pytest_report_teststatus(report, config):
    if report.when == 'call':
        if report.head_line == "test_add_remove_remotes" and report.outcome == "passed":
            test.conan_helper.TESTED_ADD_REMOVE_REMOTE = True
        if report.head_line == "test_disable_remotes" and report.outcome == "passed":
            test.conan_helper.TESTED_DISABLE_REMOTE = True


@pytest.fixture()
def conan_api():
    os.environ["CONAN_NON_INTERACTIVE"] = "True"  # don't hang is smth. goes wrong
    os.environ["CONAN_REVISIONS_ENABLED"] = "1"
    yield test.conan_api
    # delete cache file
    if (base_path / ConanInfoCache.CACHE_FILE_NAME).exists():
        try:
            os.remove(base_path / ConanInfoCache.CACHE_FILE_NAME)
        except PermissionError:  # just Windows things...
            time.sleep(5)
            os.remove(base_path / ConanInfoCache.CACHE_FILE_NAME)


@pytest.fixture(scope="session", autouse=True)
def ConanServer():
    if not check_if_process_running("conan_server", timeout_s=0):
        print("STARTING CONAN SERVER")
        start_conan_server()
    yield
    if conan_server_thread:
        print("\nKILLING CONAN SERVER\n ")
        check_if_process_running("conan_server", timeout_s=0, kill=True)
        conan_server_thread.join()


@pytest.fixture(autouse=True)
def test_output():
    print("\n********************** Starting TEST ********************************")
    yield
    print("\n********************** Finished TEST ********************************")


@pytest.fixture()
def repo_paths() -> Generator[PathSetup, None, None]:
    """
    Set up the global variables to be able to start the application.
    Needs to be used, if the tested component uses the global Logger.
    Clean up all instances after the test.
    """
    paths = PathSetup()
    yield paths
    # Teardown

def check_if_process_running(process_name, kill=False, cmd_narg=1, timeout_s=10) -> bool:
    start_time = datetime.now()
    while datetime.now() - start_time < timedelta(seconds=timeout_s) or timeout_s == 0:
        for process in psutil.process_iter():
            try:
                if process_name.lower() in process.name().lower():
                    if kill:
                        try:
                            # or parent.children() for recursive=False
                            for child in process.children(recursive=True):
                                child.terminate()
                            process.terminate()
                        except:
                            process.kill()
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, IndexError):
                pass
        print(f"Not found process {process_name}, keep looking...")
        if timeout_s == 0:
            return False
        time.sleep(1)
    return False


def run_conan_server():
    os.system("conan_server")


def start_conan_server():
    # Setup Server config
    os.system("conan_server --migrate")  # call server once to create a config file
    config_path = Path.home() / ".conan_server" / "server.conf"
    os.makedirs(str(config_path.parent), exist_ok=True)
    # configre server config file
    cp = configparser.ConfigParser()
    cp.read(str(config_path))
    # add write permissions
    if "write_permissions" not in cp:
        cp.add_section("write_permissions")
    cp["write_permissions"]["*/*@*/*"] = "*"
    with config_path.open('w', encoding="utf8") as fd:
        cp.write(fd)

    # Setup default profile
    paths = PathSetup()
    profiles_path = paths.testdata_path / "conan" / "profile"
    if conan_version.major == 1:
        conan = ConanApiFactory()
        os.makedirs(str(conan.get_profiles_path()), exist_ok=True)
        shutil.copy(str(profiles_path / platform.system().lower()),
                    conan.get_profiles_path() / "default")
    elif conan_version.major == 2:
        os.system("conan profile detect")

    # Add to firewall
    if platform.system() == "Windows":
        # check if firewall was set
        try:
            check_output(
                "netsh advfirewall firewall show rule conan_server").decode("cp850")
        except CalledProcessError:
            # allow server port for private connections
            args = f'advfirewall firewall add rule name="conan_server" program="{sys.executable}" dir= in action=allow protocol=TCP localport=9300'
            ctypes.windll.shell32.ShellExecuteW(None, "runas", "netsh", args, None, 1)
            print("Adding firewall rule for conan_server")

    # Start Server
    global conan_server_thread
    if not conan_server_thread:
        conan_server_thread = Thread(
            name="ConanServer", daemon=True, target=run_conan_server)
        conan_server_thread.start()
        time.sleep(3)
    print("ADDING CONAN REMOTE")
    clean_remotes_on_ci()
    add_remote(TEST_REMOTE_NAME, TEST_REMOTE_URL)
    login_test_remote(TEST_REMOTE_NAME)
    os.system(f"conan remote enable {TEST_REMOTE_NAME}")
    add_remote("offline_remote", "http://localhost:9999")

    create_test_data(paths)


def create_test_data(paths):
    """ Create test data """
    if SKIP_CREATE_CONAN_TEST_DATA:
        return
    print("CREATING TESTDATA FOR LOCAL CONAN SERVER")
    profiles_path = paths.testdata_path / "conan" / "profile"

    for profile in get_profiles():
        profile_path = profiles_path / profile
        create_test_ref(TEST_REF, paths, [f"-pr {str(profile_path)}",
                                          f"-o shared=False -pr {str(profile_path)}"], update=True)
        create_test_ref(TEST_REF_OFFICIAL, paths, [
                        f"-pr {str(profile_path)}"], update=True)
        if not conan_version.major == 2:
            paths = PathSetup()
            conanfile = str(paths.testdata_path / "conan" / "conanfile_no_settings.py")
            conan_create_and_upload(conanfile,  "nocompsettings/1.0.0@local/no_sets")
    # conan = ConanApi()
    # conan.init_api()
    # for i in range(9, 1000):
    #     print(f"Aliasing wiht index {i}")
    #     conan.alias(f"example/9.9.{i}@local/alias", TEST_REF)
    #     # os.system(f"conan alias example/9.9.{i}@local/alias {TEST_REF}")
